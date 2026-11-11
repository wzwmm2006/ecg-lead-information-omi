"""100/250-Hz block-averaging helpers for the frozen sensitivity analyses."""
from __future__ import annotations

import numpy as np


def reduce_window_milliseconds(*, output_samples: int, block_native_samples: int) -> dict[str, float | int]:
    """Describe the sample-based kernel without implying an anti-alias filter."""
    native_rate_hz = 500
    return {
        "output_samples": output_samples,
        "output_sampling_rate_hz": output_samples / 10.0,
        "block_native_samples": block_native_samples,
        "block_duration_ms": block_native_samples * 1000.0 / native_rate_hz,
    }


def block_mean_500hz(signal: np.ndarray, output_samples: int) -> np.ndarray:
    """Convert 500-Hz, 5,000-sample input by fixed non-overlapping block means."""
    values = np.asarray(signal, dtype=np.float32)
    if values.shape != (12, 5000):
        raise ValueError(f"Expected signal shape (12, 5000), received {values.shape}")
    if 5000 % output_samples:
        raise ValueError("output_samples must divide 5,000")
    block = 5000 // output_samples
    reduced = values.reshape(12, output_samples, block).mean(axis=2)
    return reduced.astype(np.float32)
