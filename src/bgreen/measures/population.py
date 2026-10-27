"""Residents on a 100 m grid: GHS-POP R2023A (epoch 2020) rescaled so that every unit sums to its
Census 2022 count (a simple dasymetric correction; the shape inside units comes from GHS-POP)."""
from __future__ import annotations

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from bgreen.config import RAW
from bgreen.grid import Grid

GHS = RAW / "ghs_pop" / "GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R4_C20.tif"


def ghs_on(grid: Grid) -> np.ndarray:
    with rasterio.open(GHS) as src:
        dst = np.zeros(grid.shape, dtype="float64")
        reproject(rasterio.band(src, 1), dst, dst_transform=grid.transform, dst_crs=grid.crs,
                  resampling=Resampling.sum, dst_nodata=0)
    dst[dst < 0] = 0
    return dst


def calibrated(grid100: Grid, unit_raster100: np.ndarray, census: dict, uid_to_unit: dict) -> np.ndarray:
    pop = ghs_on(grid100)
    out = np.zeros_like(pop)
    for uid, name in uid_to_unit.items():
        m = unit_raster100 == uid
        s = pop[m].sum()
        if s > 0:
            out[m] = pop[m] * census[name] / s
    return out
