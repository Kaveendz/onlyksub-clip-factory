"""
Step 2b: Detect audio volume spikes (shouting, music swells, dramatic cues)
using FFmpeg's silencedetect in reverse logic + astats windowed RMS.
Free, local, no API.

Usage:
    python scripts/detect_audio_spikes.py input_video.mp4 audio_spikes.json
"""
import json
import re
import subprocess
import sys


def detect_audio_spikes(video_path: str, window: float = 1.0, spike_db: float = -20.0) -> list[float]:
    """
    Runs ffmpeg astats per-window RMS level and returns timestamps (seconds)
    where the RMS level exceeds spike_db (i.e. a loud moment).
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-af", f"astats=metadata=1:reset={window},ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # ametadata prints "frame:N pts_time:T" then "lavfi.astats.Overall.RMS_level=X" on following lines
    timestamps = []
    pending_time = None
    for line in result.stderr.splitlines():
        t_match = re.search(r"pts_time:([\d.]+)", line)
        if t_match:
            pending_time = float(t_match.group(1))
            continue
        db_match = re.search(r"RMS_level=(-?[\d.]+)", line)
        if db_match and pending_time is not None:
            db = float(db_match.group(1))
            if db > spike_db:
                timestamps.append(pending_time)
            pending_time = None
    return timestamps


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python detect_audio_spikes.py <video_path> <output.json>", file=sys.stderr)
        sys.exit(1)

    spikes = detect_audio_spikes(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump({"audio_spike_timestamps": spikes}, f, indent=2)
    print(f"OK: found {len(spikes)} audio spikes -> {sys.argv[2]}")
