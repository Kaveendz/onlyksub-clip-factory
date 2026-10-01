from __future__ import annotations

import re
from pathlib import Path

from ..util import run
from .probe import probe


def resolve_url(url: str) -> str:
    m = re.search(r"pixeldrain\.com/u/([A-Za-z0-9]+)", url)
    if m:
        return f"https://pixeldrain.com/api/file/{m.group(1)}"
    return url


def fetch(src: str, dest: Path, validate_video: bool = False) -> Path:
    """Return a local path for `src` (local file is used as-is; URLs are downloaded
    with retries and resume support)."""
    if not re.match(r"^https?://", src):
        p = Path(src)
        if not p.exists():
            raise FileNotFoundError(src)
        return p

    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["curl", "-fL", "--retry", "5", "--retry-delay", "3", "--retry-all-errors",
         "-C", "-", "-A", "Mozilla/5.0", "-e", "https://pixeldrain.com/",
         "-o", dest, resolve_url(src)])
    if dest.stat().st_size == 0:
        raise RuntimeError(f"downloaded file is empty: {src}")
    if validate_video:
        probe(str(dest))  # raises if it's an HTML error page etc.
    return dest
