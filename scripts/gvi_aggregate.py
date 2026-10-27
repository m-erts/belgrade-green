"""Aggregate per-image GVI to 100 m cells, units and H3 hexes; validate against Global Streetscapes."""
import json

import h3
import numpy as np
import pandas as pd
from pyproj import Transformer

from bgreen.config import INTERIM, TABLES
from bgreen.grid import URBAN


def load():
    c = pd.read_parquet(INTERIM / "gvi_candidates.parquet")
    m = pd.read_parquet(INTERIM / "gvi_meta.parquet")
    s = pd.concat([pd.read_parquet(f) for f in sorted(INTERIM.glob("gvi_seg*.parquet"))], ignore_index=True)
    s = s.drop_duplicates("path")
    m["id"] = m["id"].astype(str)
    c["id"] = c["id"].astype(str)
    df = c.merge(m[["id", "path", "camera_type"]], on="id").merge(s[s.ok], on="path")
    df = df[df.camera_type == "perspective"]  # same projection as the validation set
    # one image per 100 m cell: the newest summer image, so every district is sampled the same way
    df = df.sort_values("captured_at", ascending=False).drop_duplicates(["cx", "cy"])
    df["gvi"] = df["Vegetation"]
    return df


def main():
    df = load()
    cells = df.groupby(["unit", "cx", "cy"]).agg(gvi=("gvi", "mean"), lon=("lon", "mean"), lat=("lat", "mean"),
                                                 year=("year", "max")).reset_index()
    units = cells.groupby("unit").agg(gvi_mean=("gvi", "mean"), gvi_median=("gvi", "median"),
                                      gvi_cells=("gvi", "size")).reset_index()
    units["gvi_images"] = units.unit.map(df.groupby("unit").size())
    cells["hex8"] = [h3.latlng_to_cell(a, b, 8) for a, b in zip(cells.lat, cells.lon)]
    hexes = cells.groupby("hex8").agg(gvi=("gvi", "mean"), gvi_cells=("gvi", "size")).reset_index()
    cells.to_parquet(INTERIM / "gvi_cells.parquet")
    hexes.to_parquet(INTERIM / "gvi_hex8.parquet")
    units.to_csv(TABLES / "units_gvi.csv", index=False)
    meta = {"images": int(len(df)), "cells": int(len(cells)), "years": df.year.value_counts().sort_index().to_dict(),
            "months": df.month.value_counts().sort_index().to_dict()}
    val = INTERIM / "gvi_validation.parquet"
    if val.exists():
        v = pd.read_parquet(val)
        meta["validation"] = {"n": int(len(v)), "pearson": float(np.corrcoef(v.gvi_ours, v.gvi_gs)[0, 1]),
                              "mean_abs_diff": float((v.gvi_ours - v.gvi_gs).abs().mean()),
                              "mean_diff": float((v.gvi_ours - v.gvi_gs).mean())}
    (TABLES / "gvi_meta.json").write_text(json.dumps(meta, indent=1, default=int))
    um = pd.read_csv(TABLES / "units_measures.csv")
    um = um.drop(columns=[c for c in um.columns if c.startswith("gvi_")]).merge(units, on="unit", how="left")
    um.to_csv(TABLES / "units_measures.csv", index=False)
    print(units.round(3).to_string(index=False))
    print(meta)


if __name__ == "__main__":
    main()
