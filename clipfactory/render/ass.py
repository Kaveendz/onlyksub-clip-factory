from __future__ import annotations

from ..config import Config
from ..models import Line
from .layout import Layout


def _ts(sec: float) -> str:
    sec = max(0.0, sec)
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _text(t: str) -> str:
    return t.replace("{", "(").replace("}", ")").replace("\\", "").replace("\n", "\\N")


def build_ass(lines: list[Line], clip_start: float, clip_end: float, layout: Layout,
              cfg: Config, hook_text: str = "") -> str:
    dur = clip_end - clip_start
    W, H = layout.out_w, layout.out_h
    vertical = layout.mode == "blur"

    if vertical:
        sub_size = cfg.sub_size_vertical
        band_top = (H - layout.fg_h) // 2
        bottom_area = H - (band_top + layout.fg_h)
        sub_mv = int(max(300, min(cfg.vertical_sub_margin_v, bottom_area - 40)))
        hook_size, hook_mv = 72, cfg.vertical_hook_margin_v
        wm_size, wm_mv = 34, max(100, band_top - 90)
        margin_lr = 80
    else:
        scale = H / 1080
        sub_size = int(cfg.sub_size_wide * scale)
        hook_size, hook_mv = int(60 * scale), int(60 * scale)
        wm_size, wm_mv = int(28 * scale), int(30 * scale)
        sub_mv = int(60 * scale)
        margin_lr = int(120 * scale)

    outline = max(2, round(sub_size / 14))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{cfg.font_name},{sub_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},0,2,{margin_lr},{margin_lr},{sub_mv},1
Style: Hook,{cfg.font_name},{hook_size},&H0000D7FF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline + 1},0,8,{margin_lr},{margin_lr},{hook_mv},1
Style: Mark,{cfg.font_name},{wm_size},&H80FFFFFF,&H000000FF,&H80000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,9,40,40,{wm_mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev: list[str] = []
    for l in lines:
        if l.end <= clip_start or l.start >= clip_end:
            continue
        s = max(0.0, l.start - clip_start)
        e = min(dur, l.end - clip_start)
        if e - s < 0.15:
            continue
        ev.append(f"Dialogue: 0,{_ts(s)},{_ts(e)},Sub,,0,0,0,,{_text(l.text)}")
    if hook_text:
        ev.append(f"Dialogue: 1,{_ts(0)},{_ts(min(cfg.hook_seconds, dur))},Hook,,0,0,0,,"
                  f"{{\\fad(200,300)}}{_text(hook_text)}")
    if cfg.watermark_text:
        ev.append(f"Dialogue: 2,{_ts(0)},{_ts(dur)},Mark,,0,0,0,,{_text(cfg.watermark_text)}")
    return head + "\n".join(ev) + "\n"
