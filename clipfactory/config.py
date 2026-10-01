from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class Config:
    # ---- selection ----
    clip_count: int = 6
    min_len: float = 15.0
    max_len: float = 45.0
    target_len: float = 30.0
    candidate_pool: int = 15
    nms_overlap: float = 0.3        # max allowed overlap between two chosen clips
    skip_head: float = 90.0         # skip intro/recap (only for long episodes)
    skip_tail: float = 120.0        # skip credits
    skip_threshold: float = 600.0   # head/tail skipping only if episode is longer than this
    peak_radius: int = 15           # seconds: a heat peak must be the max within +-radius
    end_slack: float = 4.0          # how far past the peak we may look for a clean end
    start_pad: float = 0.15
    end_pad: float = 0.4
    scene_threshold: float = 0.3
    # ---- render ----
    modes: tuple = ("blur", "wide")  # blur = 9:16 full-frame + blurred bg ; wide = original 16:9
    crf: int = 18
    preset: str = "medium"
    audio_bitrate: str = "192k"
    normalize_audio: bool = True
    # ---- subtitles / overlays ----
    font_name: str = "Noto Sans Sinhala"
    sub_size_vertical: int = 64
    sub_size_wide: int = 48          # at 1080p height, scaled for other heights
    vertical_sub_margin_v: int = 430  # keeps subs above TikTok/Reels bottom UI
    vertical_hook_margin_v: int = 300
    hook_seconds: float = 4.0
    watermark_text: str = "OnlyKSub"

    @classmethod
    def from_overrides(cls, overrides: dict | None) -> "Config":
        cfg = cls()
        for f in fields(cls):
            if overrides and overrides.get(f.name) is not None:
                v = overrides[f.name]
                cur = getattr(cfg, f.name)
                if isinstance(cur, tuple):
                    v = tuple(x.strip() for x in v.split(",")) if isinstance(v, str) else tuple(v)
                elif isinstance(cur, bool):
                    v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")
                else:
                    v = type(cur)(v)
                setattr(cfg, f.name, v)
        return cfg
