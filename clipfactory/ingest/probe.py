from __future__ import annotations

import json
import re
from collections import Counter

from ..models import VideoInfo
from ..util import run


def probe(path: str) -> VideoInfo:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path])
    d = json.loads(r.stdout)
    video = next((s for s in d["streams"] if s.get("codec_type") == "video"
                  and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    if video is None:
        raise RuntimeError(f"no video stream in {path}")
    duration = float(d["format"].get("duration") or video.get("duration") or 0)
    if duration <= 0:
        raise RuntimeError(f"could not determine duration of {path}")
    num, _, den = (video.get("avg_frame_rate") or "25/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 25.0
    return VideoInfo(
        path=path,
        width=int(video["width"]),
        height=int(video["height"]),
        duration=duration,
        fps=fps or 25.0,
        has_audio=any(s.get("codec_type") == "audio" for s in d["streams"]),
    )


def detect_crop(path: str, width: int, height: int, duration: float) -> str | None:
    """Detect letterbox/pillarbox black bars. Needs 2 of 3 samples to agree
    (a single dark scene must not shrink the frame)."""
    votes: Counter = Counter()
    for frac in (0.25, 0.5, 0.75):
        r = run(
            ["ffmpeg", "-hide_banner", "-ss", f"{duration * frac:.2f}", "-i", path, "-t", "3",
             "-vf", "cropdetect=limit=24:round=2:reset=0", "-an", "-f", "null", "-"],
            check=False,
        )
        found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
        if found:
            votes[":".join(found[-1])] += 1
    if not votes:
        return None
    crop, count = votes.most_common(1)[0]
    cw, ch, _, _ = (int(v) for v in crop.split(":"))
    if count < 2:
        return None
    if cw * ch >= 0.98 * width * height:      # nothing meaningful to crop
        return None
    if cw < 0.5 * width or ch < 0.5 * height:  # implausible
        return None
    return crop
