"""Classic class-level landscape metrics (FRAGSTATS names) for one habitat class."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from bgreen.connectivity.graph import euclidean_links


def class_metrics(habitat: np.ndarray, area_mask: np.ndarray, res: float, min_area_ha: float = 0.0):
    cell = res * res / 1e4
    hab = habitat & area_mask
    lab, n = ndi.label(hab, structure=np.ones((3, 3), dtype=bool))
    sizes = np.bincount(lab.ravel())[1:] * cell
    keep = sizes >= min_area_ha
    sizes_k = sizes[keep]
    A = area_mask.sum() * cell
    # edge: habitat/non-habitat pixel sides inside the area of interest
    e = 0
    for ax in (0, 1):
        a = np.swapaxes(hab, 0, ax)
        m = np.swapaxes(area_mask, 0, ax)
        diff = (a[1:] != a[:-1]) & m[1:] & m[:-1]
        e += diff.sum()
    edge_m = e * res
    out = {
        "PLAND_pct": 100 * hab.sum() * cell / A,
        "NP": int(keep.sum()),
        "PD_per_100ha": 100 * keep.sum() / A,
        "AREA_MN_ha": float(sizes_k.mean()) if len(sizes_k) else 0.0,
        "AREA_MD_ha": float(np.median(sizes_k)) if len(sizes_k) else 0.0,
        "LPI_pct": 100 * float(sizes_k.max()) / A if len(sizes_k) else 0.0,
        "ED_m_per_ha": edge_m / A,
        "MESH_ha": float((sizes_k ** 2).sum() / A),
        "landscape_ha": float(A),
    }
    if keep.sum() > 1:
        remap = np.zeros(n + 1, dtype=np.int32)
        remap[1:][keep] = np.arange(1, keep.sum() + 1)
        el = euclidean_links(remap[lab], area_mask, res)
        nn = np.full(keep.sum(), np.inf)
        np.minimum.at(nn, el["i"].to_numpy() - 1, el["dist"].to_numpy())
        np.minimum.at(nn, el["j"].to_numpy() - 1, el["dist"].to_numpy())
        nn = nn[np.isfinite(nn)]
        out["ENN_MN_m"] = float(nn.mean())
        out["ENN_MD_m"] = float(np.median(nn))
    return out
