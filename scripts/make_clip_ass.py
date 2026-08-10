"""
Step 3c-prep: Given the full parsed dialogue (from parse_subtitle.py) and
a clip's [start, end] window, produce a standalone .ass file for just
that clip - re-timed so the clip's subtitles start at 00:00:00.

Usage:
    python scripts/make_clip_ass.py dialogue.json "00:02:40.243" "00:02:50.253" \
        clip_1.ass "OnlyKSub Clip Sans" 48
"""
import sys
import json


def parse_ts(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def secs_to_ass_ts(secs: float) -> str:
    secs = max(0.0, secs)
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


ASS_HEADER_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def make_clip_ass(dialogue_path: str, clip_start: str, clip_end: str,
                   out_path: str, font_name: str, font_size: int) -> None:
    with open(dialogue_path, "r", encoding="utf-8") as f:
        dialogue = json.load(f)

    start_s = parse_ts(clip_start)
    end_s = parse_ts(clip_end)

    lines = [ASS_HEADER_TEMPLATE.format(font_name=font_name, font_size=font_size)]
    count = 0
    for entry in dialogue:
        d_start = parse_ts(entry["start"])
        d_end = parse_ts(entry["end"])
        if d_end < start_s or d_start > end_s:
            continue
        rel_start = max(0.0, d_start - start_s)
        rel_end = max(0.0, d_end - start_s)
        text = entry["text"].replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{secs_to_ass_ts(rel_start)},{secs_to_ass_ts(rel_end)},Default,,0,0,0,,{text}\n"
        )
        count += 1

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"OK: {count} subtitle lines written -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print(
            "Usage: python make_clip_ass.py <dialogue.json> <clip_start> <clip_end> "
            "<out.ass> <font_name> <font_size>",
            file=sys.stderr,
        )
        sys.exit(1)
    make_clip_ass(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6]))
