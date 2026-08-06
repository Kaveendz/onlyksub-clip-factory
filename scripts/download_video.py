"""
Step 1a: Download the source video from a Pixeldrain (or direct) URL.

Usage:
    python scripts/download_video.py "<video_url>" output/input_video.mp4
"""
import re
import subprocess
import sys
from pathlib import Path


def resolve_pixeldrain_url(url: str) -> str:
    """If it's a pixeldrain share link, convert it to the direct file API URL."""
    match = re.search(r"pixeldrain\.com/u/([a-zA-Z0-9]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://pixeldrain.com/api/file/{file_id}"
    return url


def download_video(url: str, out_path: str) -> None:
    resolved = resolve_pixeldrain_url(url)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "curl", "-f", "-L",
        "-A", "Mozilla/5.0",
        "-e", "https://pixeldrain.com/",
        "-o", str(out),
        resolved,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: download failed\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Validate it's actually a video file, not an error page
    file_check = subprocess.run(["file", str(out)], capture_output=True, text=True)
    if not re.search(r"MP4|Matroska|ISO Media|WebM", file_check.stdout):
        print(f"ERROR: downloaded file is not a valid video.\n{file_check.stdout}", file=sys.stderr)
        sys.exit(1)

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"OK: downloaded {out} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python download_video.py <video_url> <output_path>", file=sys.stderr)
        sys.exit(1)
    download_video(sys.argv[1], sys.argv[2])
