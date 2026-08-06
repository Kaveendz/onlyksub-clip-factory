"""
Step 1c: Parse .srt or .ass into a clean, timestamped dialogue list.

Output format (JSON):
[
  {"start": "00:01:12.340", "end": "00:01:15.100", "text": "..."},
  ...
]

Usage:
    python scripts/parse_subtitle.py subs.srt parsed_dialogue.json
"""
import json
import re
import sys
from pathlib import Path


def _ts_to_str(h, m, s, ms):
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{int(ms):03d}"


def parse_srt(text: str) -> list[dict]:
    entries = []
    blocks = re.split(r"\n\s*\n", text.strip())
    time_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
    )
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        time_line = next((l for l in lines if "-->" in l), None)
        if not time_line:
            continue
        m = time_re.search(time_line)
        if not m:
            continue
        start = _ts_to_str(*m.groups()[0:4])
        end = _ts_to_str(*m.groups()[4:8])
        text_lines = lines[lines.index(time_line) + 1:]
        clean_text = " ".join(text_lines).strip()
        clean_text = re.sub(r"<[^>]+>", "", clean_text)  # strip HTML-ish tags
        clean_text = re.sub(r"\{\\[^}]*\}", "", clean_text).strip()  # strip {\an8} etc position tags
        if clean_text:
            entries.append({"start": start, "end": end, "text": clean_text})
    return entries


def parse_ass(text: str) -> list[dict]:
    entries = []
    dialogue_re = re.compile(
        r"^Dialogue:\s*[^,]*,([\d:.]+),([\d:.]+),.*?,,\d*,\d*,\d*,[^,]*,(.*)$"
    )
    for line in text.splitlines():
        m = dialogue_re.match(line.strip())
        if not m:
            continue
        start_raw, end_raw, raw_text = m.groups()
        # ASS timestamps are H:MM:SS.CS (centiseconds) -> normalize to H:MM:SS.mmm
        def norm(ts):
            h, mnt, rest = ts.split(":")
            s, cs = rest.split(".")
            ms = int(cs) * 10
            return _ts_to_str(h, mnt, s, ms)

        clean_text = re.sub(r"\{[^}]*\}", "", raw_text)  # strip ASS style overrides
        clean_text = clean_text.replace("\\N", " ").replace("\\n", " ").strip()
        if clean_text:
            entries.append({"start": norm(start_raw), "end": norm(end_raw), "text": clean_text})
    return entries


def parse_subtitle_file(path: str) -> list[dict]:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    if p.suffix.lower() == ".ass":
        return parse_ass(text)
    return parse_srt(text)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python parse_subtitle.py <subs.srt|subs.ass> <output.json>", file=sys.stderr)
        sys.exit(1)

    entries = parse_subtitle_file(sys.argv[1])
    if not entries:
        print("ERROR: no dialogue entries parsed — check the subtitle file format.", file=sys.stderr)
        sys.exit(1)

    Path(sys.argv[2]).write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: parsed {len(entries)} dialogue lines -> {sys.argv[2]}")
