"""
Step 3c: Burn subtitles into a reframed clip using clip-factory's own
custom font/style (independent from the main site's subtitle styling).

Usage:
    python scripts/burn_clip_subs.py clip_vertical.mp4 subs.ass output.mp4 fonts/
"""
import subprocess
import sys


def burn_subs(video_path: str, ass_path: str, output_path: str, fonts_dir: str) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"ass={ass_path}:fontsdir={fonts_dir}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR burning subs into {output_path}:\n{result.stderr[-1000:]}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: subs burned -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python burn_clip_subs.py <clip.mp4> <subs.ass> <output.mp4> <fonts_dir>",
            file=sys.stderr,
        )
        sys.exit(1)
    burn_subs(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
