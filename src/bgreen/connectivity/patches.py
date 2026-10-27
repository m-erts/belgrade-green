"""Habitat patches: 8-connected tree-cover components above a minimum area."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from bgreen.grid import Grid


def label_patches(habitat: np.ndarray, grid: Grid, min_area_ha: float = 1.0):
    """Return (labels, areas_ha). Labels are 1..n in decreasing order of area; 0 = not a patch."""
    lab, n = ndi.label(habitat, structure=np.ones((3, 3), dtype=bool))
    cell_ha = grid.res * grid.res / 1e4
    counts = np.bincount(lab.ravel(), minlength=n + 1)
    counts[0] = 0
    keep = np.flatnonzero(counts * cell_ha >= min_area_ha)
    order = keep[np.argsort(-counts[keep], kind="stable")]
    remap = np.zeros(n + 1, dtype=np.int32)
    remap[order] = np.arange(1, len(order) + 1, dtype=np.int32)
    labels = remap[lab]
    areas = counts[order] * cell_ha
    return labels, areas


def patch_table(labels: np.ndarray, areas: np.ndarray, grid: Grid):
    import pandas as pd

    n = len(areas)
    idx = np.arange(1, n + 1)
    rows, cols = np.nonzero(labels)
    lab = labels[rows, cols]
    cy = np.bincount(lab, weights=rows, minlength=n + 1)[1:] / np.bincount(lab, minlength=n + 1)[1:]
    cx = np.bincount(lab, weights=cols, minlength=n + 1)[1:] / np.bincount(lab, minlength=n + 1)[1:]
    x = grid.left + (cx + 0.5) * grid.res
    y = grid.top - (cy + 0.5) * grid.res
    return pd.DataFrame({"patch": idx, "area_ha": areas, "x": x, "y": y})
