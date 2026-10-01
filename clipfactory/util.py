from __future__ import annotations

import subprocess


def run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(
            f"command failed ({r.returncode}): {' '.join(str(c) for c in cmd[:5])} ...\n{r.stderr[-1500:]}"
        )
    return r


def fmt_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def esc_filter_path(p: str) -> str:
    """Escape a file path for use inside an ffmpeg filter argument."""
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
