from __future__ import annotations

import math

import numpy as np

from ..models import Line


def _smooth(x: np.ndarray, k: int) -> np.ndarray:
    if k <= 1 or len(x) == 0:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def _norm(x: np.ndarray) -> np.ndarray:
    """Scale to 0..1 using the 95th percentile (robust against one huge outlier)."""
    if len(x) == 0 or not np.any(x > 0):
        return np.zeros_like(x)
    p = np.percentile(x, 95)
    return np.clip(x / (p if p > 1e-9 else x.max()), 0.0, 1.0)


def build_heat(duration: float, audio_energy: np.ndarray, scenes: list[float],
               lines: list[Line]) -> tuple[np.ndarray, dict]:
    """Combine all free local signals into one 'drama heat' value per second (0..1)."""
    n = int(math.ceil(duration))

    audio = np.zeros(n)
    audio[: min(n, len(audio_energy))] = audio_energy[:n]
    audio_n = _norm(_smooth(audio, 3))

    cuts = np.zeros(n)
    for t in scenes:
        if 0 <= int(t) < n:
            cuts[int(t)] += 1
    cuts_n = _norm(_smooth(cuts, 5))

    speech = np.zeros(n)
    for l in lines:
        dur = max(l.end - l.start, 0.5)
        cps = len(l.text) / dur
        for s in range(max(0, int(l.start)), min(n, int(math.ceil(l.end)))):
            overlap = min(s + 1, l.end) - max(s, l.start)
            if overlap > 0:
                speech[s] += cps * overlap
    speech_n = _norm(_smooth(speech, 5))

    if lines:
        raw = 0.45 * audio_n + 0.20 * cuts_n + 0.35 * speech_n
    else:
        raw = 0.65 * audio_n + 0.35 * cuts_n
    heat = _smooth(raw, 5)
    return heat, {"audio": audio_n, "cuts": cuts_n, "speech": speech_n}
