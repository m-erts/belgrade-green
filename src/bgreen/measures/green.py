"""Public green space from OSM: parks, gardens, forests and woods that are not private."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from rasterio.features import rasterize

from bgreen.config import RAW
from bgreen.grid import Grid

PRIVATE = {"private", "no", "customers", "residents", "permit"}


def public_green(crs) -> gpd.GeoDataFrame:
    g = gpd.read_file(RAW / "osm_green.gpkg").to_crs(crs)
    leisure = g["leisure"].isin(["park", "garden", "nature_reserve"])
    landuse = g["landuse"].isin(["forest", "recreation_ground", "village_green"])
    natural = g["natural"].isin(["wood"])
    sel = g[(leisure | landuse | natural) & ~g["access"].isin(PRIVATE)]
    if "garden:type" in sel:
        sel = sel[~sel["garden:type"].isin(["residential", "private"])]
    return sel


def dissolved(crs) -> gpd.GeoDataFrame:
    """Union of all public green polygons, split into contiguous pieces with their area."""
    u = public_green(crs).geometry.buffer(0).union_all()
    parts = gpd.GeoDataFrame(geometry=[u], crs=crs).explode(index_parts=False).reset_index(drop=True)
    parts["area_ha"] = parts.area / 1e4
    return parts


def mask(parts: gpd.GeoDataFrame, grid: Grid) -> np.ndarray:
    return rasterize([(geom, 1) for geom in parts.geometry], out_shape=grid.shape, transform=grid.transform,
                     fill=0, dtype="uint8").astype(bool)
