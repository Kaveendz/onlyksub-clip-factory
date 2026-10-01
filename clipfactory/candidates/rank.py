from __future__ import annotations

from ..config import Config
from ..models import Candidate


def heuristic_rank(candidates: list[Candidate], cfg: Config) -> list[Candidate]:
    """Phase 1 ranking: purely signal-based. (Phase 2 replaces/augments this with the
    Gemini ranker, which picks among these pre-snapped candidates by id.)"""
    ordered = sorted(candidates, key=lambda c: -c.score)[: cfg.clip_count]
    for i, c in enumerate(ordered, start=1):
        c.rank = i
    return ordered
