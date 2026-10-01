import json

from clipfactory.config import Config
from clipfactory.ingest.probe import detect_crop, probe
from clipfactory.models import Job
from clipfactory.pipeline import run_pipeline
from clipfactory.signals.scenes import detect_scenes
from tests.conftest import needs_ffmpeg
from tests.fixture import make_video

pytestmark = needs_ffmpeg


def test_scene_detection_finds_the_real_cuts(episode):
    cuts = detect_scenes(episode[0])
    assert len(cuts) == 14 and abs(cuts[0] - 10.0) < 0.5


def test_black_bars_detected_only_when_present(tmp_path, episode):
    i = probe(episode[0])
    assert detect_crop(i.path, i.width, i.height, i.duration) is None
    bars = make_video(tmp_path / "bars.mp4", pad_bars=True)
    j = probe(bars)
    assert detect_crop(j.path, j.width, j.height, j.duration) == "1280:540:0:90"


def test_end_to_end_both_layouts(tmp_path, episode):
    cfg = Config.from_overrides({"clip_count": 2, "preset": "ultrafast", "crf": 28})
    rep = run_pipeline(Job(video=episode[0], srt=episode[1], drama_name="T"), cfg, str(tmp_path))
    assert rep["summary"]["rendered_ok"] == rep["summary"]["total"] == 4
    assert rep["needs_review"] is True                         # source_status defaults to "unknown"
    top = rep["clips"][0]
    assert 15 <= top["duration"] <= 46
    assert top["qa"]["blur"]["size"] == "1080x1920" and top["qa"]["wide"]["size"] == "1280x720"
    assert all(q["has_audio"] and q["ok"] for c in rep["clips"] for q in c["qa"].values())


def test_resume_from_stage_reuses_artifacts(tmp_path, episode):
    cfg = Config.from_overrides({"clip_count": 1, "preset": "ultrafast", "crf": 28, "modes": "wide"})
    run_pipeline(Job(video=episode[0], srt=episode[1]), cfg, str(tmp_path))
    first = json.loads((tmp_path / "selected.json").read_text())
    rep = run_pipeline(Job(video=episode[0], srt=episode[1]), cfg, str(tmp_path), from_stage="render")
    assert rep["summary"]["rendered_ok"] == 1
    assert rep["clips"][0]["id"] == first[0]["id"]            # same selection, reused not recomputed
