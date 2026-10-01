from __future__ import annotations

import numpy as np

from ..config import Config
from ..models import Candidate, Line


def _find_peaks(heat: np.ndarray, lo: float, hi: float, radius: int) -> list[int]:
    peaks = []
    for i in range(max(0, int(lo)), min(len(heat), int(hi))):
        if heat[i] <= 0:
            continue
        window = heat[max(0, i - radius): i + radius + 1]
        if heat[i] >= window.max():
            peaks.append(i)
    return sorted(peaks, key=lambda i: -heat[i])


def _pick_end(t: float, lines: list[Line], scenes: list[float], duration: float, cfg: Config) -> float:
    """Cliffhanger end: finish at the end of the line being spoken at the peak (or the
    first one after it) - never mid-sentence, and never after the resolution.
    The heat curve is smoothed, so the peak is only accurate to ~2 s: a line that ended
    just before it is a valid clean end too."""
    after = [l.end for l in lines if t <= l.end <= t + cfg.end_slack]
    before = [l.end for l in lines if t - 2.0 <= l.end < t]
    if after:
        end = min(after)
    elif before:
        end = max(before)
    else:
        cuts = [s for s in scenes if t <= s <= t + cfg.end_slack]
        end = min(cuts) if cuts else t + 1.5
    return min(duration, end + cfg.end_pad)


def _pick_start(end: float, heat: np.ndarray, lines: list[Line], scenes: list[float],
                cfg: Config) -> float:
    """Start on a natural boundary (a line that follows silence, or a scene cut)."""
    lo, hi = end - cfg.max_len, end - cfg.min_len
    bounds: list[tuple[float, float]] = []  # (time, bonus)
    prev_end = -99.0
    for l in lines:
        if lo <= l.start <= hi:
            bonus = 0.10 if l.start - prev_end >= 0.8 else 0.0
            bounds.append((l.start, bonus))
        prev_end = max(prev_end, l.end)
    for s in scenes:
        if lo <= s <= hi:
            bounds.append((s, 0.05))
    if not bounds:
        return max(0.0, end - cfg.target_len)

    def value(b: tuple[float, float]) -> float:
        t, bonus = b
        window = heat[int(t): int(end) + 1]
        mean = float(window.mean()) if len(window) else 0.0
        length_fit = 1.0 - min(1.0, abs((end - t) - cfg.target_len) / cfg.target_len)
        return mean + bonus + 0.10 * length_fit

    best_t, _ = max(bounds, key=value)
    return max(0.0, best_t - cfg.start_pad)


def _overlap(a: Candidate, b: Candidate) -> float:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    return inter / max(1e-9, min(a.duration, b.duration))


def build_candidates(heat: np.ndarray, lines: list[Line], scenes: list[float],
                     duration: float, cfg: Config) -> list[Candidate]:
    long_ep = duration > cfg.skip_threshold
    lo = cfg.skip_head if long_ep else 0.0
    hi = duration - (cfg.skip_tail if long_ep else 0.0)
    hmax = float(heat.max()) if len(heat) and heat.max() > 0 else 1.0

    raw: list[Candidate] = []
    for i, peak in enumerate(_find_peaks(heat, lo, hi, cfg.peak_radius)[: cfg.candidate_pool * 4]):
        end = _pick_end(float(peak), lines, scenes, duration, cfg)
        start = _pick_start(end, heat, lines, scenes, cfg)
        if not (cfg.min_len <= end - start <= cfg.max_len + 1):
            continue
        seg = heat[int(start): int(end) + 1]
        hook = heat[int(start): int(start) + 3]
        tail = heat[max(0, int(end) - 3): int(end) + 1]
        mean, hook_m, end_m = float(seg.mean()), float(hook.mean()), float(tail.mean())
        score = round(min(10.0, 10 * (0.5 * mean + 0.3 * hook_m + 0.2 * end_m) / hmax), 2)
        n_lines = sum(1 for l in lines if l.end > start and l.start < end)
        n_cuts = sum(1 for s in scenes if start <= s <= end)
        raw.append(Candidate(
            id=0, start=round(start, 2), end=round(end, 2), score=score,
            heat_mean=round(mean, 3), hook_heat=round(hook_m, 3), end_heat=round(end_m, 3),
            n_lines=n_lines, n_cuts=n_cuts,
            reason=f"heat peak at {peak}s; {n_lines} dialogue lines, {n_cuts} scene cuts",
        ))

    chosen: list[Candidate] = []
    for c in sorted(raw, key=lambda c: -c.score):
        if all(_overlap(c, k) <= cfg.nms_overlap for k in chosen):
            chosen.append(c)
        if len(chosen) >= cfg.candidate_pool:
            break
    for i, c in enumerate(chosen, start=1):
        c.id = i
    return chosen
