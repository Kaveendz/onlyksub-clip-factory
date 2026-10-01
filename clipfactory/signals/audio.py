from __future__ import annotations

import subprocess

import numpy as np

SR = 8000


def loudness_per_second(video_path: str, has_audio: bool = True) -> np.ndarray:
    """Per-second RMS loudness in dB (index = second). Streams mono 8 kHz PCM from
    ffmpeg and measures it in numpy, so one value really is one second."""
    if not has_audio:
        return np.zeros(0)
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video_path, "-vn", "-ac", "1", "-ar", str(SR),
         "-f", "s16le", "-"],
        capture_output=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"audio extraction failed: {p.stderr.decode(errors='replace')[-500:]}")
    x = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    n = len(x) // SR
    if n == 0:
        return np.zeros(0)
    chunks = x[: n * SR].reshape(n, SR)
    rms = np.sqrt((chunks ** 2).mean(axis=1))
    return 20 * np.log10(rms + 1e-9)


def drama_energy(db: np.ndarray, window: int = 61) -> np.ndarray:
    """Dramatic energy per second = how much louder than its own surroundings
    (rise over a rolling median) + a smaller bonus for being loud overall.
    Relative to the episode itself, so quiet and loud sources behave the same."""
    if len(db) == 0:
        return db
    db = np.maximum(db, -80.0)
    pad = window // 2
    padded = np.pad(db, pad, mode="edge")
    baseline = np.median(np.lib.stride_tricks.sliding_window_view(padded, window), axis=-1)
    rise = np.maximum(db - baseline, 0.0)
    loud = np.maximum(db - np.percentile(db, 60), 0.0)
    return rise + 0.5 * loud
