import numpy as np

def center_config(x, channel_idx):
    """A2a centring. x: (trials, 12, T) 50 Hz mV. Returns (z, c)."""
    channel_idx = tuple(int(i) for i in channel_idx)
    if not channel_idx:
        raise ValueError("empty channel list")
    if len(set(channel_idx)) != len(channel_idx):
        raise ValueError("duplicate channel")
    if min(channel_idx) < 0 or max(channel_idx) >= x.shape[1]:
        raise ValueError("channel out of range")
    sub = x[:, channel_idx, :]
    medians = np.median(sub, axis=2)
    c = medians.mean(axis=1, keepdims=True)
    z = (sub - c[:, :, None]) / 1.0
    return z, c


def center_reference(x, channel_idx):
    """Independent reference: explicit loop over leads."""
    channel_idx = list(channel_idx)
    out = np.empty((x.shape[0], len(channel_idx), x.shape[2]), dtype=np.float64)
    c = np.empty((x.shape[0], 1), dtype=np.float64)
    for n in range(x.shape[0]):
        ms = [float(np.median(x[n, l, :])) for l in channel_idx]
        ci = sum(ms) / len(ms)
        c[n, 0] = ci
        for j, l in enumerate(channel_idx):
            out[n, j, :] = (x[n, l, :] - ci) / 1.0
    return out, c