"""Meta / WRI High Resolution Canopy Height (Tolan et al. 2024), ~1 m, aggregated to the 10 m grid.

Each 10 m cell gets the share of its area where predicted canopy height is at or above a
threshold, i.e. canopy cover. Tiles are strip-organised GeoTIFFs in EPSG:3857, so they are
downloaded whole (data/raw/meta_chm) and read block by block."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

from bgreen.config import RAW
from bgreen.grid import Grid

TILE_DIR = RAW / "meta_chm"
THRESHOLDS = (2, 3, 5)


def canopy_cover(grid: Grid, out_path: Path = RAW / "canopy_cover_meta.tif", block_rows=128,
                 thresholds=THRESHOLDS):
    if out_path.exists():
        return out_path
    tiles = sorted(TILE_DIR.glob("*.tif"))
    out = np.full((len(thresholds) + 1, grid.height, grid.width), np.nan, dtype="float32")
    for r0 in range(0, grid.height, block_rows):
        nrows = min(block_rows, grid.height - r0)
        top = grid.top - r0 * grid.res
        sub = Grid(grid.left, top, grid.width, nrows, grid.res, grid.crs)
        for tp in tiles:
            with rasterio.open(tp) as src:
                b = transform_bounds(grid.crs, src.crs, *sub.bounds, densify_pts=21)
                win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
                win = win.intersection(Window(0, 0, src.width, src.height)) if _overlaps(win, src) else None
                if win is None:
                    continue
                pad = Window(max(win.col_off - 16, 0), max(win.row_off - 16, 0),
                             min(win.width + 32, src.width - max(win.col_off - 16, 0)),
                             min(win.height + 32, src.height - max(win.row_off - 16, 0)))
                h = src.read(1, window=pad)
                tr = src.window_transform(pad)
                for k in range(len(thresholds) + 1):
                    layer = (h >= thresholds[k]).astype("float32") if k < len(thresholds) else h.astype("float32")
                    dst = np.full(sub.shape, np.nan, dtype="float32")
                    reproject(layer, dst, src_transform=tr, src_crs=src.crs, dst_transform=sub.transform,
                              dst_crs=grid.crs, resampling=Resampling.average, src_nodata=None,
                              dst_nodata=np.nan)
                    blk = out[k, r0:r0 + nrows]
                    fill = np.isnan(blk) & np.isfinite(dst)
                    blk[fill] = dst[fill]
        print(f"rows {r0}-{r0 + nrows} / {grid.height}", flush=True)
    prof = grid.profile("float32", np.nan, count=len(thresholds) + 1)
    with rasterio.open(out_path, "w", **prof) as d:
        for k in range(len(thresholds) + 1):
            d.write(out[k], k + 1)
        for k, t in enumerate(thresholds):
            d.set_band_description(k + 1, f"share of area with canopy height >= {t} m")
        d.set_band_description(len(thresholds) + 1, "mean canopy height, m")
    return out_path


def _overlaps(win: Window, src) -> bool:
    return not (win.col_off >= src.width or win.row_off >= src.height or
                win.col_off + win.width <= 0 or win.row_off + win.height <= 0)
