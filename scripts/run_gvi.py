"""Green View Index for the 10 urban units from Mapillary summer images.

1. list images from Mapillary coverage tiles (z14) over the units;
2. keep perspective (non-panorama) images taken May-September, daytime by month only;
3. thin spatially: per 100 m cell keep the two newest summer images (2019 or later) from different sequences;
4. fetch metadata (thumbnail URL, camera type) and download 1024 px thumbnails;
5. segmentation is a separate step in the project venv (bgreen.measures.segment).
Usage: python scripts/run_gvi.py list | fetch"""
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.warp import transform_bounds

from bgreen.config import INTERIM
from bgreen.data import mapillary as mly
from bgreen.grid import URBAN
from bgreen.measures import units

CELL = 100.0
PER_CELL = 2  # the second image per cell is kept as a reserve; aggregation uses the newest
MONTHS = range(5, 10)
MIN_YEAR = 2019


def candidates():
    u = units.load(URBAN.crs)
    bbox = transform_bounds(URBAN.crs, "EPSG:4326", *u.total_bounds, densify_pts=21)
    df = mly.coverage(bbox, z=14)
    print("images in tiles:", len(df), flush=True)
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(URBAN.crs)
    g = gpd.sjoin(g, u[["unit", "geometry"]], how="inner", predicate="within").drop(columns="index_right")
    g["year"] = g.captured_at.dt.year
    g["month"] = g.captured_at.dt.month
    print("in units:", len(g), "| by year:", g.year.value_counts().sort_index().to_dict(), flush=True)
    s = g[(~g.is_pano.astype(bool)) & g.month.isin(MONTHS) & (g.year >= MIN_YEAR)].copy()
    print("summer, non-pano, >= MIN_YEAR:", len(s), flush=True)
    s["cx"] = (s.geometry.x // CELL).astype(int)
    s["cy"] = (s.geometry.y // CELL).astype(int)
    s = s.sort_values(["cx", "cy", "captured_at"], ascending=[True, True, False])
    s = s.drop_duplicates(["cx", "cy", "sequence_id"])  # one image per sequence per cell
    s = s.groupby(["cx", "cy"]).head(PER_CELL)
    print("thinned:", len(s), "cells:", s[["cx", "cy"]].drop_duplicates().shape[0], flush=True)
    print(s.groupby("unit").size().to_dict(), flush=True)
    s.drop(columns="geometry").to_parquet(INTERIM / "gvi_candidates.parquet")
    return s


def fetch():
    s = pd.read_parquet(INTERIM / "gvi_candidates.parquet")
    meta_path = INTERIM / "gvi_meta.parquet"
    have = pd.read_parquet(meta_path) if meta_path.exists() else pd.DataFrame({"id": []})
    todo = s[~s.id.astype(str).isin(have["id"].astype(str))]
    print("metadata to fetch:", len(todo), flush=True)
    for k in range(0, len(todo), 2000):
        part = mly.entities(todo.id.iloc[k:k + 2000].tolist())
        part["path"] = mly.download(part)
        have = pd.concat([have, part], ignore_index=True)
        have.to_parquet(meta_path)
        print(f"{min(k + 2000, len(todo))}/{len(todo)}  ok={part['path'].notna().sum()}", flush=True)
    ok = have[have["path"].notna() & (have.get("camera_type", "perspective") != "spherical")]
    (INTERIM / "gvi_paths.txt").write_text("\n".join(ok["path"].astype(str)))
    print("thumbnails ready:", len(ok), flush=True)


if __name__ == "__main__":
    {"list": candidates, "fetch": fetch}[sys.argv[1]]()
