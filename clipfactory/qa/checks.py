from __future__ import annotations

import json
import subprocess

from ..render.layout import Layout
from ..util import run


def check_clip(path: str, layout: Layout, expected_dur: float) -> dict:
    """Cheap automatic QA: right size, right length, has audio, not a black picture."""
    d = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_streams", "-show_format", path]).stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    dur = float(d["format"]["duration"])

    frame = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{min(1.0, dur / 2):.2f}", "-i", path,
         "-frames:v", "1", "-vf", "scale=32:18", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True,
    ).stdout
    brightness = (sum(frame) / len(frame)) if frame else 0.0

    problems = []
    if (v["width"], v["height"]) != (layout.out_w, layout.out_h):
        problems.append(f"size {v['width']}x{v['height']} != {layout.out_w}x{layout.out_h}")
    if abs(dur - expected_dur) > 0.6:
        problems.append(f"duration {dur:.2f}s != expected {expected_dur:.2f}s")
    if not has_audio:
        problems.append("no audio track")
    if brightness < 6:
        problems.append("picture looks black")
    return {"ok": not problems, "problems": problems, "duration": round(dur, 2),
            "size": f"{v['width']}x{v['height']}", "has_audio": has_audio,
            "brightness": round(brightness, 1)}
