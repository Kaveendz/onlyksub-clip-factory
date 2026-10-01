from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Line:
    start: float
    end: float
    text: str


@dataclass
class VideoInfo:
    path: str
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool
    crop: str | None = None  # "w:h:x:y" if black bars were detected

    def content_size(self) -> tuple[int, int]:
        if self.crop:
            w, h, _, _ = (int(v) for v in self.crop.split(":"))
            return w, h
        return self.width, self.height


@dataclass
class Candidate:
    id: int
    start: float
    end: float
    score: float
    heat_mean: float = 0.0
    hook_heat: float = 0.0
    end_heat: float = 0.0
    n_lines: int = 0
    n_cuts: int = 0
    reason: str = ""
    hook_text: str = ""     # filled by the LLM stage (Phase 2)
    emotion: str = ""       # filled by the LLM stage (Phase 2)
    rank: int = 0

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Job:
    video: str
    srt: str | None = None
    drama_name: str = ""
    source_status: str = "unknown"   # licensed | permitted | unknown
    options: dict = field(default_factory=dict)


def to_dict(obj) -> dict:
    return asdict(obj)
