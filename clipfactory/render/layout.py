from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Layout:
    mode: str      # "blur" | "wide"
    out_w: int
    out_h: int
    fg_h: int      # height of the real picture inside the frame
    blur_bg: bool  # blurred background behind a letterboxed picture?
    cover: bool    # portrait source: fill the frame instead


def make_layout(src_w: int, src_h: int, mode: str) -> Layout:
    if mode == "blur":
        # Full source picture is kept (nothing cropped), centred on a blurred copy.
        if src_w / src_h <= 9 / 16 + 0.01:
            return Layout(mode, 1080, 1920, 1920, blur_bg=False, cover=True)
        fg_h = int(round(src_h * 1080 / src_w / 2)) * 2
        return Layout(mode, 1080, 1920, fg_h, blur_bg=True, cover=False)
    if mode == "wide":
        # Original aspect ratio, never upscaled, capped at 1920 wide.
        w = min(src_w, 1920)
        w -= w % 2
        h = int(round(src_h * w / src_w / 2)) * 2
        return Layout(mode, w, h, h, blur_bg=False, cover=False)
    raise ValueError(f"unknown mode: {mode}")
