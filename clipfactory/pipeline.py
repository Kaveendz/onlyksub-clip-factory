from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .candidates.build import build_candidates
from .candidates.rank import heuristic_rank
from .config import Config
from .ingest.download import fetch
from .ingest.probe import detect_crop, probe
from .ingest.subtitle import parse_subtitle_file
from .models import Candidate, Job, Line, VideoInfo
from .qa.checks import check_clip
from .render.ass import build_ass
from .render.ffmpeg_cmd import build_cmd
from .render.layout import make_layout
from .signals.audio import drama_energy, loudness_per_second
from .signals.heatmap import build_heat
from .signals.scenes import detect_scenes
from .util import fmt_ts, run

log = logging.getLogger("clipfactory")
STAGES = ["ingest", "signals", "candidates", "rank", "render"]
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"


class Workdir:
    def __init__(self, path: str | Path):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=True)

    def p(self, name: str) -> Path:
        return self.root / name

    def save(self, name: str, obj) -> None:
        self.p(name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, name: str):
        f = self.p(name)
        if not f.exists():
            raise FileNotFoundError(f"{f} missing - run an earlier stage first (--from-stage)")
        return json.loads(f.read_text(encoding="utf-8"))


def run_pipeline(job: Job, cfg: Config, workdir: str, from_stage: str = "ingest") -> dict:
    wd = Workdir(workdir)
    first = STAGES.index(from_stage)
    t0 = time.time()

    # ---------------------------------------------------------------- 1. ingest
    if first <= 0:
        log.info("[1/5] ingest")
        video = fetch(job.video, wd.p("source_video.mp4"), validate_video=True)
        info = probe(str(video))
        info.crop = detect_crop(str(video), info.width, info.height, info.duration)
        lines: list[Line] = []
        if job.srt:
            sub_path = fetch(job.srt, wd.p("source_subs.srt"))
            lines = parse_subtitle_file(sub_path)
            if not lines:
                raise RuntimeError("subtitle file parsed to zero lines - check its format")
        wd.save("info.json", asdict(info))
        wd.save("dialogue.json", [asdict(l) for l in lines])
        log.info("      %dx%d  %.0fs  crop=%s  subtitle lines=%d",
                 info.width, info.height, info.duration, info.crop, len(lines))
    else:
        info = VideoInfo(**wd.load("info.json"))
        lines = [Line(**d) for d in wd.load("dialogue.json")]

    # --------------------------------------------------------------- 2. signals
    if first <= 1:
        log.info("[2/5] signals (audio energy, scene cuts, speech density)")
        db = loudness_per_second(info.path, info.has_audio)
        energy = drama_energy(db)
        scenes = detect_scenes(info.path, cfg.scene_threshold)
        heat, parts = build_heat(info.duration, energy, scenes, lines)
        wd.save("signals.json", {
            "scenes": scenes,
            "audio_db": np.round(db, 1).tolist(),
            "heat": np.round(heat, 3).tolist(),
            "parts": {k: np.round(v, 3).tolist() for k, v in parts.items()},
        })
        log.info("      %d scene cuts, peak heat %.2f", len(scenes), heat.max() if len(heat) else 0)
    else:
        sig = wd.load("signals.json")
        scenes, heat = sig["scenes"], np.array(sig["heat"])

    # ------------------------------------------------------------ 3. candidates
    if first <= 2:
        log.info("[3/5] candidate windows (snapped to dialogue / scene boundaries)")
        candidates = build_candidates(heat, lines, scenes, info.duration, cfg)
        wd.save("candidates.json", [asdict(c) for c in candidates])
        log.info("      %d candidates", len(candidates))
    else:
        candidates = [Candidate(**d) for d in wd.load("candidates.json")]

    # ------------------------------------------------------------------ 4. rank
    if first <= 3:
        log.info("[4/5] rank")
        selected = heuristic_rank(candidates, cfg)
        wd.save("selected.json", [asdict(c) for c in selected])
    else:
        selected = [Candidate(**d) for d in wd.load("selected.json")]

    # ---------------------------------------------------------------- 5. render
    log.info("[5/5] render %d clips x modes %s", len(selected), list(cfg.modes))
    out_dir = wd.p("clips")
    out_dir.mkdir(exist_ok=True)
    cw, ch = info.content_size()
    results = []
    for c in selected:
        entry = {"rank": c.rank, "id": c.id, "start": fmt_ts(c.start), "end": fmt_ts(c.end),
                 "duration": round(c.duration, 2), "score": c.score, "reason": c.reason,
                 "hook_text": c.hook_text, "emotion": c.emotion, "files": {}, "qa": {}}
        for mode in cfg.modes:
            layout = make_layout(cw, ch, mode)
            name = f"clip_{c.rank:02d}_{mode}"
            ass_path = wd.p(f"{name}.ass")
            ass_path.write_text(build_ass(lines, c.start, c.end, layout, cfg, c.hook_text), encoding="utf-8")
            out_path = out_dir / f"{name}.mp4"
            try:
                run(build_cmd(info, c.start, c.end, layout, str(ass_path), str(FONTS_DIR),
                              str(out_path), cfg))
                qa = check_clip(str(out_path), layout, c.duration)
                entry["files"][mode] = str(out_path)
                entry["qa"][mode] = qa
                log.info("      %s  %s  %s", name, qa["size"], "OK" if qa["ok"] else f"QA FAIL {qa['problems']}")
            except Exception as e:  # one failed clip must not kill the batch
                entry["qa"][mode] = {"ok": False, "problems": [str(e)[-300:]]}
                log.error("      %s FAILED: %s", name, str(e)[-300:])
        results.append(entry)

    ok = sum(1 for r in results for q in r["qa"].values() if q.get("ok"))
    total = sum(len(r["qa"]) for r in results)
    report = {
        "drama_name": job.drama_name,
        "source_status": job.source_status,
        "needs_review": job.source_status != "licensed",
        "source": {"width": info.width, "height": info.height, "duration": info.duration,
                   "crop": info.crop},
        "clips": results,
        "summary": {"rendered_ok": ok, "total": total, "seconds": round(time.time() - t0, 1)},
    }
    wd.save("report.json", report)
    log.info("done: %d/%d renders OK in %.0fs", ok, total, time.time() - t0)
    return report
