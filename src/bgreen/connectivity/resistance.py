"""Resistance surface for a generalist woodland species, built from ESA WorldCover and OSM.

Units: a 10 m step through tree cover costs 10; the values below are multipliers. They are an
expert-based assumption (documented in docs/methodology.md) and are varied in the sensitivity runs."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from rasterio.features import rasterize

from bgreen.grid import Grid

# WorldCover class -> resistance multiplier
LANDCOVER = {
    "main": {10: 1, 20: 2, 30: 4, 90: 4, 40: 15, 60: 15, 80: 50, 50: 60, 0: 60},
    "permeable": {10: 1, 20: 1.5, 30: 2, 90: 2, 40: 8, 60: 8, 80: 25, 50: 30, 0: 30},
    "strict": {10: 1, 20: 3, 30: 8, 90: 8, 40: 30, 60: 30, 80: 100, 50: 120, 0: 120},
    "water_barrier": {10: 1, 20: 2, 30: 4, 90: 4, 40: 15, 60: 15, 80: 500, 50: 60, 0: 60},
}

# OSM linear barriers: (resistance multiplier, burnt width in metres)
ROADS = {
    "motorway": (1000, 30), "trunk": (500, 25), "primary": (300, 20), "secondary": (150, 15),
    "tertiary": (100, 12), "motorway_link": (300, 10), "trunk_link": (200, 10),
    "primary_link": (150, 10), "secondary_link": (100, 10), "tertiary_link": (80, 10),
}
RAIL = {"rail": (100, 10), "light_rail": (80, 8)}
ROAD_SCALE = {"main": 1.0, "permeable": 0.5, "strict": 2.0, "water_barrier": 1.0}


def build(landcover: np.ndarray, grid: Grid, barriers: gpd.GeoDataFrame, scenario: str = "main") -> np.ndarray:
    lut = np.full(256, LANDCOVER[scenario][0], dtype="float32")
    for k, v in LANDCOVER[scenario].items():
        lut[k] = v
    res = lut[landcover]
    b = barriers.to_crs(grid.crs)
    elevated = b.get("bridge", None)
    tunnel = b.get("tunnel", None)
    on_ground = np.ones(len(b), dtype=bool)
    if elevated is not None:
        on_ground &= elevated.isna() | (elevated == "no")
    if tunnel is not None:
        on_ground &= tunnel.isna() | (tunnel == "no")
    b = b[on_ground]
    shapes = []
    for kind, table in (("highway", ROADS), ("railway", RAIL)):
        if kind not in b:
            continue
        for cls, (r, width) in table.items():
            sel = b[b[kind] == cls]
            if len(sel):
                r_eff = r * ROAD_SCALE[scenario]
                shapes += [(geom, r_eff) for geom in sel.geometry.buffer(width / 2)]
    # burn in order of increasing resistance so the strongest barrier wins where they overlap
    shapes.sort(key=lambda s: s[1])
    burnt = rasterize(shapes, out_shape=grid.shape, transform=grid.transform, fill=0, dtype="float32",
                      all_touched=False)
    return np.maximum(res, burnt)
