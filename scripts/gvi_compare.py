"""Compare the five measures: unit ranks and hexagon-level agreement."""
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from bgreen.config import INTERIM, TABLES

MEAS = ["ndvi_mean", "tree_cover_wc_pct", "canopy3_meta_pct", "gvi_mean", "green_m2_per_person", "within300_1ha_pct"]

if __name__ == "__main__":
    um = pd.read_csv(TABLES / "units_measures.csv").set_index("unit")
    ms = [m for m in MEAS if m in um]
    ranks = um[ms].rank(ascending=False, method="min").astype(int)
    print(pd.concat([um[ms].round(3), ranks.add_suffix("_rank")], axis=1).to_string())
    rho = um[ms].corr(method="spearman").round(2)
    print(rho.to_string())
    out = {"unit_spearman": rho.to_dict(), "rank_span": (ranks.max(axis=1) - ranks.min(axis=1)).to_dict()}
    hx = pd.read_parquet(INTERIM / "hex8_measures.parquet")
    g = pd.read_parquet(INTERIM / "gvi_hex8.parquet").set_index("hex8")
    h = hx.join(g, how="inner")
    h = h[h.gvi_cells >= 10]
    cols = ["ndvi", "wc_tree", "canopy", "gvi"]
    print("hexes with >= 10 GVI cells:", len(h))
    rh = h[cols].corr(method="spearman").round(2)
    print(rh.to_string())
    out["hex_n"] = int(len(h))
    out["hex_spearman"] = rh.to_dict()
    # where NDVI and GVI disagree most: rank difference
    h["r_ndvi"] = h.ndvi.rank(pct=True)
    h["r_gvi"] = h.gvi.rank(pct=True)
    h["gap"] = h.r_ndvi - h.r_gvi
    print("NDVI >> GVI (green from above, grey from the street):")
    print(h.sort_values("gap", ascending=False).head(8)[["unit", "ndvi", "canopy", "gvi", "density", "gap"]].round(3))
    print("GVI >> NDVI (grey from above, green from the street):")
    print(h.sort_values("gap").head(8)[["unit", "ndvi", "canopy", "gvi", "density", "gap"]].round(3))
    by_unit = h.groupby("unit").gap.mean().sort_values()
    print(by_unit.round(3))
    out["gap_by_unit"] = by_unit.round(4).to_dict()
    (TABLES / "gvi_compare.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
