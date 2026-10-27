"""Access-based measures on a fine grid.

two_step_fca: m² of public green within `radius` per resident, with every green cell shared among
all residents within `radius` of it (2SFCA, Luo & Wang 2003). Distance is straight-line, as in
the Belgrade green-system plan (2019) norm of 7 / 10 / 23 m² within 300 m."""
from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve


def disk(radius_m: float, res: float) -> np.ndarray:
    r = int(np.ceil(radius_m / res))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return ((x * res) ** 2 + (y * res) ** 2 <= radius_m ** 2).astype("float64")


def _conv(a, k):
    out = fftconvolve(a, k, mode="same")
    out[np.abs(out) < 1e-9] = 0
    return out


def two_step_fca(green_m2: np.ndarray, pop: np.ndarray, radius_m: float, res: float) -> np.ndarray:
    k = disk(radius_m, res)
    demand = _conv(pop, k)                       # residents who can reach each green cell
    ratio = np.where((green_m2 > 0) & (demand > 0), green_m2 / np.maximum(demand, 1e-9), 0.0)
    return _conv(ratio, k)                      # m² per resident available at each home cell


def within(mask: np.ndarray, radius_m: float, res: float) -> np.ndarray:
    """Cells within `radius_m` (straight line) of any True cell."""
    from scipy import ndimage as ndi
    d = ndi.distance_transform_edt(~mask) * res
    return d <= radius_m
