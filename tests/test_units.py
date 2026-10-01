import numpy as np

from clipfactory.candidates.build import build_candidates
from clipfactory.config import Config
from clipfactory.ingest.subtitle import parse_ass, parse_srt
from clipfactory.models import Line
from clipfactory.render.ass import build_ass
from clipfactory.render.layout import make_layout
from clipfactory.signals.audio import drama_energy
from clipfactory.util import fmt_ts


def test_parse_srt_strips_tags_and_handles_crlf_bom_free():
    srt = "1\r\n00:00:01,500 --> 00:00:03,000\r\n<i>Hello</i> {\\an8}there\r\n\r\n2\r\n00:01:00.000 --> 00:01:02.250\r\nA\r\nB\r\n"
    lines = parse_srt(srt)
    assert [(l.start, l.end, l.text) for l in lines] == [(1.5, 3.0, "Hello there"), (60.0, 62.25, "A B")]


def test_parse_ass_uses_format_line_and_keeps_commas_in_text():
    ass = """[Script Info]
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,{\\an8}Well, hello\\Nthere
"""
    (l,) = parse_ass(ass)
    assert (l.start, l.end, l.text) == (1.0, 2.5, "Well, hello there")


def test_fmt_ts():
    assert fmt_ts(3725.5) == "01:02:05.500"


def test_layouts_cover_both_modes():
    v = make_layout(1920, 1080, "blur")
    assert (v.out_w, v.out_h, v.fg_h, v.blur_bg) == (1080, 1920, 608, True)  # full picture kept
    w = make_layout(1920, 1080, "wide")
    assert (w.out_w, w.out_h) == (1920, 1080)
    small = make_layout(1280, 720, "wide")
    assert (small.out_w, small.out_h) == (1280, 720)          # never upscaled
    assert make_layout(1080, 1920, "blur").cover               # portrait source fills the frame


def test_audio_energy_is_relative_to_surroundings():
    db = np.full(300, -40.0)
    db[100:105] = -15.0                                        # a loud moment
    e = drama_energy(db)
    assert e[102] > 20 and e[10] == 0 and e[250] == 0


def test_candidates_end_on_line_boundary_and_respect_length():
    cfg = Config()
    heat = np.zeros(200)
    heat[60:75] = np.linspace(0.2, 1.0, 15)
    lines = [Line(30, 33, "a"), Line(40, 44, "b"), Line(50, 56, "c"), Line(62, 70, "d"), Line(71, 73.3, "e")]
    cands = build_candidates(heat, lines, [], 200.0, cfg)
    assert cands
    c = cands[0]
    assert cfg.min_len <= c.duration <= cfg.max_len + 1
    ends = [l.end + cfg.end_pad for l in lines]
    assert any(abs(c.end - e) < 0.02 for e in ends)            # ends right after a spoken line
    starts = [l.start - cfg.start_pad for l in lines]
    assert any(abs(c.start - s) < 0.02 for s in starts)        # starts on a spoken line


def test_ass_is_retimed_clamped_and_escaped():
    cfg = Config()
    lay = make_layout(1920, 1080, "blur")
    ass = build_ass([Line(9.0, 12.0, "before {x}"), Line(20.0, 100.0, "runs past end"),
                     Line(500.0, 510.0, "outside")], 10.0, 40.0, lay, cfg, hook_text="WAIT...")
    assert "PlayResX: 1080" in ass and "PlayResY: 1920" in ass
    assert "0:00:00.00,0:00:02.00,Sub,,0,0,0,,before (x)" in ass   # starts clamped to 0, braces escaped
    assert "0:00:10.00,0:00:30.00,Sub,,0,0,0,,runs past end" in ass  # end clamped to clip length
    assert "outside" not in ass and "WAIT..." in ass and "OnlyKSub" in ass
