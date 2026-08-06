"""
Step 2a: Detect visual scene-changes in the video (free, local, no API).
Catches silent/dialogue-free moments that subtitles can't tell us about.

Usage:
    python scripts/detect_scenes.py input_video.mp4 scenes.json
"""
import json
import re
import subprocess
import sys


def detect_scenes(video_path: str, threshold: float = 0.3) -> list[float]:
    """Returns a list of timestamps (seconds) where a scene change is detected."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # showinfo prints to stderr; pts_time:XX.XX is what we want
    timestamps = [float(m) for m in re.findall(r"pts_time:([\d.]+)", result.stderr)]
    return timestamps


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python detect_scenes.py <video_path> <output.json>", file=sys.stderr)
        sys.exit(1)

    scenes = detect_scenes(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump({"scene_change_timestamps": scenes}, f, indent=2)
    print(f"OK: found {len(scenes)} scene changes -> {sys.argv[2]}")
