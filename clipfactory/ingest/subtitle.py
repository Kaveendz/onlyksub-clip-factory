from __future__ import annotations

import re
from pathlib import Path

from ..models import Line

_SRT_TIME = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})"
)
_TAGS = re.compile(r"<[^>]+>|\{[^}]*\}")


def _secs(h, m, s, frac, scale=1000) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(frac.ljust(3, "0")[:3]) / 1000


def _clean(text: str) -> str:
    text = _TAGS.sub("", text)
    text = text.replace("\\N", " ").replace("\\n", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_srt(text: str) -> list[Line]:
    out: list[Line] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip()):
        lines = block.strip().split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        m = _SRT_TIME.search(lines[idx])
        if not m:
            continue
        g = m.groups()
        start, end = _secs(*g[0:4]), _secs(*g[4:8])
        body = _clean(" ".join(lines[idx + 1:]))
        if body and end > start:
            out.append(Line(start, end, body))
    return out


def parse_ass(text: str) -> list[Line]:
    out: list[Line] = []
    fields: list[str] = []
    in_events = False
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line.lower().startswith("[events]"):
            in_events = True
            continue
        if line.startswith("[") and in_events:
            break
        if not in_events:
            continue
        if line.lower().startswith("format:"):
            fields = [f.strip().lower() for f in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("dialogue:") and fields:
            parts = line.split(":", 1)[1].lstrip().split(",", len(fields) - 1)
            if len(parts) != len(fields):
                continue
            row = dict(zip(fields, parts))
            try:
                def t(v):
                    h, m, rest = v.strip().split(":")
                    s, cs = rest.split(".")
                    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs.ljust(2, "0")[:2]) / 100
                start, end = t(row["start"]), t(row["end"])
            except (KeyError, ValueError):
                continue
            body = _clean(row.get("text", ""))
            if body and end > start:
                out.append(Line(start, end, body))
    return out


def parse_subtitle_file(path: str | Path) -> list[Line]:
    p = Path(path)
    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    head = text[:2000].lower()
    lines = parse_ass(text) if (p.suffix.lower() in (".ass", ".ssa") or "[script info]" in head) else parse_srt(text)
    lines.sort(key=lambda l: (l.start, l.end))
    seen, unique = set(), []
    for l in lines:
        key = (round(l.start, 2), round(l.end, 2), l.text)
        if key not in seen:
            seen.add(key)
            unique.append(l)
    return unique
