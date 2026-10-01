import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(scope="session")
def episode(tmp_path_factory):
    from tests.fixture import make_srt, make_video
    d = tmp_path_factory.mktemp("ep")
    return make_video(d / "ep.mp4"), make_srt(d / "ep.srt")
