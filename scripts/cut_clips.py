"""
Step 3a: Cut the source video at each approved Gemini-selected moment.

Usage:
    python scripts/cut_clips.py input_video.mp4 moments.json work/clips_raw/
"""
import json
import subprocess
import sys
from pathlib import Path


def cut_clip(video_path: str, start: str, end: str, out_path: str) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", start,
        "-to", end,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "160k",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR cutting {out_path}:\n{result.stderr[-1000:]}", file=sys.stderr)
        sys.exit(1)


def cut_all_clips(video_path: str, moments_path: str, out_dir: str) -> list[str]:
    with open(moments_path, "r", encoding="utf-8") as f:
        moments = json.load(f)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for i, m in enumerate(moments):
        clip_path = out / f"clip_{i + 1}.mp4"
        cut_clip(video_path, m["start"], m["end"], str(clip_path))
        clip_paths.append(str(clip_path))
        print(f"OK: cut clip {i + 1} ({m['start']} -> {m['end']}) -> {clip_path}")

    return clip_paths


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python cut_clips.py <video_path> <moments.json> <out_dir>", file=sys.stderr)
        sys.exit(1)

    paths = cut_all_clips(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"OK: {len(paths)} clips cut")
