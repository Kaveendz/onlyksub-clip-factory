"""
Step 1b: Download the subtitle file (.srt or .ass) from a raw URL
(e.g. a GitHub Gist raw_url, same pattern as the sub-burn repo).

Usage:
    python scripts/download_subtitle.py "<srt_url>" output/subs.srt
"""
import subprocess
import sys
from pathlib import Path


def download_subtitle(url: str, out_path: str) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["curl", "-f", "-L", "-o", str(out), url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: subtitle download failed\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    content = out.read_text(encoding="utf-8", errors="ignore")
    if not content.strip():
        print("ERROR: downloaded subtitle file is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"OK: downloaded {out} ({len(content)} chars)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python download_subtitle.py <srt_url> <output_path>", file=sys.stderr)
        sys.exit(1)
    download_subtitle(sys.argv[1], sys.argv[2])
