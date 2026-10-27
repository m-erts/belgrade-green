"""Human-readable names for patches: the named OSM green area covering most of the patch's
pixels, plus the nearest OSM place name to the patch centroid."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.features import rasterize

from bgreen.config import RAW
from bgreen.grid import Grid


def _label(df):
    lat = df["name:sr-Latn"] if "name:sr-Latn" in df else pd.Series(index=df.index, dtype=object)
    return lat.fillna(df["name"])


def name_patches(labels: np.ndarray, grid: Grid, ids=None) -> pd.DataFrame:
    g = gpd.read_file(RAW / "osm_green.gpkg").to_crs(grid.crs)
    g = g[g["name"].notna()].copy()
    g["label"] = _label(g)
    g["area"] = g.area
    g = g.sort_values("area", ascending=False).reset_index(drop=True)  # small features drawn last win
    gid = rasterize([(geom, i + 1) for i, geom in enumerate(g.geometry)], out_shape=grid.shape,
                    transform=grid.transform, fill=0, dtype="int32")
    pl = gpd.read_file(RAW / "osm_places.gpkg").to_crs(grid.crs)
    pl = pl[pl["name"].notna()].copy()
    pl["label"] = _label(pl)
    m = labels > 0
    lab, nid = labels[m], gid[m]
    n = labels.max()
    rows = []
    want = set(range(1, n + 1)) if ids is None else set(ids)
    order = np.argsort(lab, kind="stable")
    lab_s, nid_s = lab[order], nid[order]
    starts = np.searchsorted(lab_s, np.arange(1, n + 2))
    rr, cc = np.nonzero(m)
    rr, cc = rr[order], cc[order]
    for p in sorted(want):
        a, b = starts[p - 1], starts[p]
        if a == b:
            continue
        ids_here = nid_s[a:b]
        named = ids_here[ids_here > 0]
        if len(named):
            vals, cnt = np.unique(named, return_counts=True)
            k = vals[np.argmax(cnt)]
            green_name, share = g.loc[k - 1, "label"], cnt.max() / (b - a)
        else:
            green_name, share = None, 0.0
        cx = grid.left + (cc[a:b].mean() + 0.5) * grid.res
        cy = grid.top - (rr[a:b].mean() + 0.5) * grid.res
        d = np.hypot(pl.geometry.x - cx, pl.geometry.y - cy)
        rows.append({"patch": p, "green_name": green_name, "green_share": round(float(share), 3),
                     "near_place": pl.iloc[int(np.argmin(d))]["label"], "x": cx, "y": cy})
    return pd.DataFrame(rows)
