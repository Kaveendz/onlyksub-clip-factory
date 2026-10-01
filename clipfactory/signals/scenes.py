from __future__ import annotations

import re

from ..util import run


def detect_scenes(video_path: str, threshold: float = 0.3) -> list[float]:
    """Visual cut timestamps (seconds). Downscaled + sampled at 5 fps first, so a
    full episode is analysed quickly."""
    r = run(
        ["ffmpeg", "-hide_banner", "-i", video_path, "-an",
         "-vf", f"fps=5,scale=320:-2,select='gt(scene,{threshold})',showinfo",
         "-f", "null", "-"],
        check=False,
    )
    times = sorted({round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)})
    return times
