"""Summer NDVI from Sentinel-2 L2A (Earth Search, collection 1), median of clear observations."""
from __future__ import annotations

import json
import os
import time

import numpy as np
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from bgreen.config import CACHE, RAW
from bgreen.grid import Grid

os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
SCENE_CACHE = CACHE / "s2_ndvi"
SCENE_CACHE.mkdir(parents=True, exist_ok=True)

STAC = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-c1-l2a"
CLEAR_SCL = (4, 5, 6)  # vegetation, not vegetated, water


def search(bbox_ll, start="2025-06-01", end="2025-08-31", max_cloud=5.0, tile="34TDQ"):
    body = {"collections": [COLLECTION], "bbox": list(bbox_ll),
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": max_cloud}}, "limit": 200}
    items = requests.post(STAC, json=body, timeout=120).json()["features"]
    items = [i for i in items if i["id"].split("_")[1] == "T" + tile]
    # one acquisition per day and orbit is enough; keep the clearer one
    best = {}
    for it in items:
        key = (it["properties"]["datetime"][:10], it["properties"].get("sat:relative_orbit"))
        if key not in best or it["properties"]["eo:cloud_cover"] < best[key]["properties"]["eo:cloud_cover"]:
            best[key] = it
    return sorted(best.values(), key=lambda i: i["properties"]["datetime"])


def _band(item, name):
    a = item["assets"][name]
    rb = (a.get("raster:bands") or [{}])[0]
    return a["href"], rb.get("scale", 1.0), rb.get("offset", 0.0)


def _read(href, grid: Grid, resampling, attempts=4):
    for k in range(attempts):
        try:
            with rasterio.open(href) as src, WarpedVRT(
                src, crs=grid.crs, transform=grid.transform, width=grid.width, height=grid.height,
                resampling=resampling, nodata=0,
            ) as vrt:
                return vrt.read(1)
        except rasterio.errors.RasterioIOError:
            if k == attempts - 1:
                raise
            time.sleep(10 * (k + 1))


def ndvi_scene(item, grid: Grid):
    out = {}
    for b in ("red", "nir"):
        href, scale, offset = _band(item, b)
        dn = _read(href, grid, Resampling.nearest).astype("float32")
        refl = np.where(dn > 0, dn * scale + offset, np.nan)
        out[b] = refl
    scl = _read(item["assets"]["scl"]["href"], grid, Resampling.nearest)
    red, nir = out["red"], out["nir"]
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = (nir - red) / (nir + red)
    ndvi[~np.isin(scl, CLEAR_SCL)] = np.nan
    ndvi[(red <= 0) | (nir <= 0)] = np.nan
    return ndvi.astype("float32")


def summer_ndvi(grid: Grid, bbox_ll, out_path=RAW / "ndvi_summer2025.tif", **kw):
    if out_path.exists():
        return out_path
    items = search(bbox_ll, **kw)
    stack, used = [], []
    for it in items:
        cache = SCENE_CACHE / f"{it['id']}_{grid.left:.0f}_{grid.top:.0f}.npy"
        if cache.exists():
            nd = np.load(cache).astype("float32") / 10000
            nd[nd < -1.5] = np.nan
        else:
            nd = ndvi_scene(it, grid)
            np.save(cache, np.where(np.isfinite(nd), np.round(nd * 10000), -32768).astype("int16"))
        valid = np.isfinite(nd).mean()
        used.append({"id": it["id"], "date": it["properties"]["datetime"][:10],
                     "cloud": it["properties"]["eo:cloud_cover"], "valid_share": round(float(valid), 4)})
        print(used[-1], flush=True)
        if valid > 0.05:
            stack.append(nd)
    arr = np.stack(stack)
    med = np.nanmedian(arr, axis=0).astype("float32")
    n = np.isfinite(arr).sum(axis=0).astype("uint8")
    prof = grid.profile("float32", np.nan, count=2)
    with rasterio.open(out_path, "w", **prof) as d:
        d.write(med, 1)
        d.write(n.astype("float32"), 2)
        d.set_band_description(1, "median NDVI of clear observations")
        d.set_band_description(2, "number of clear observations")
    (out_path.with_suffix(".json")).write_text(json.dumps(used, indent=1))
    return out_path
