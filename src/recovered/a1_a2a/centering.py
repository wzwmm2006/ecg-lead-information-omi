"""A2a configuration-local amplitude-preserving centering."""
from __future__ import annotations

import numpy as np


def center_config_precenter(
    amplitude_mv: np.ndarray,
    channels: list[int],
    *,
    fixed_scale_mv: float = 1.0,
) -> dict[str, np.ndarray | float]:
    """Center each selected lead on the configuration mean of per-lead medians.

    Non-finite values are replaced by 0 mV before centering. The scale is fixed
    at 1 mV. The returned ``z`` contains only the selected leads.
    """
    values = np.asarray(amplitude_mv, dtype=np.float64)
    if values.ndim != 3:
        raise ValueError("amplitude_mv must have shape (N, leads, time)")
    if not channels:
        raise ValueError("channels must be non-empty")
    if max(channels) >= values.shape[1] or min(channels) < 0:
        raise ValueError("channel index out of range")

    selected = values[:, channels, :]
    replaced = np.nan_to_num(selected, nan=0.0, posinf=0.0, neginf=0.0)
    per_lead_median = np.median(replaced, axis=2)
    center_mv = float(np.mean(per_lead_median))
    z = np.nan_to_num(
        (replaced - center_mv) / fixed_scale_mv,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    return {"z": z.astype(np.float32), "center_mv": center_mv, "scale_mv": fixed_scale_mv}
