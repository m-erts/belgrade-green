"""ESA WorldCover 2021 v200 (10 m), read as a window straight from the public S3 bucket."""
from __future__ import annotations

import math

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject

from bgreen.config import RAW
from bgreen.grid import CITY, Grid

URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"

CLASSES = {
    10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland", 50: "Built-up",
    60: "Bare / sparse vegetation", 70: "Snow and ice", 80: "Permanent water bodies",
    90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss and lichen",
}


def tiles_for_bbox(west, south, east, north):
    """WorldCover tiles are 3x3 degrees, named by their lower-left corner."""
    out = []
    for lat in range(int(math.floor(south / 3) * 3), int(math.ceil(north / 3) * 3), 3):
        for lon in range(int(math.floor(west / 3) * 3), int(math.ceil(east / 3) * 3), 3):
            ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
            ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
            out.append(f"{ns}{ew}")
    return out


def fetch(grid: Grid = CITY, out_path=RAW / "worldcover_2021.tif"):
    """Mosaic the tiles that cover the grid and reproject them (nearest neighbour) onto it."""
    if out_path.exists():
        return out_path
    from rasterio.warp import transform_bounds

    west, south, east, north = transform_bounds(grid.crs, "EPSG:4326", *grid.bounds, densify_pts=21)
    pad = 0.01
    srcs = [rasterio.open("/vsicurl/" + URL.format(tile=t)) for t in tiles_for_bbox(west, south, east, north)]
    mosaic, transform = merge(srcs, bounds=(west - pad, south - pad, east + pad, north + pad), nodata=0)
    dst = np.zeros(grid.shape, dtype=np.uint8)
    reproject(mosaic[0], dst, src_transform=transform, src_crs=srcs[0].crs,
              dst_transform=grid.transform, dst_crs=grid.crs, resampling=Resampling.nearest,
              src_nodata=0, dst_nodata=0)
    with rasterio.open(out_path, "w", **grid.profile("uint8", 0)) as d:
        d.write(dst, 1)
    for s in srcs:
        s.close()
    return out_path
