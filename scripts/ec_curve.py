"""EC as a share of habitat area across dispersal distances, for the main run and its variants."""
import json

import numpy as np
import pandas as pd

from bgreen.config import INTERIM, TABLES
from bgreen.connectivity import pc

D50 = np.unique(np.r_[np.round(np.logspace(np.log10(50), np.log10(30000), 37)).astype(int), [100, 300, 1000, 3000, 10000]])

if __name__ == "__main__":
    rows = []
    for name in ["main", "permeable", "strict", "water_barrier", "min05ha", "nodes_touching",
                 "city", "city_min05ha", "city_permeable", "city_strict"]:
        d = INTERIM / f"conn_{name}"
        if not (d / "links.parquet").exists():
            continue
        a = np.load(d / "areas.npy")
        D = pc.apsp(pc.adjacency(len(a), pd.read_parquet(d / "links.parquet")))
        for d50 in D50:
            e = pc.ec(D, a, float(d50))
            rows.append({"run": name, "d50": int(d50), "ec_ha": e, "habitat_ha": a.sum(), "ec_share": e / a.sum(),
                         "ec0_share": np.sqrt((a ** 2).sum()) / a.sum()})
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "ec_curve.csv", index=False)
    print(df[df.d50.isin([100, 300, 1000, 3000, 10000]) | (df.d50 == df.d50.min())].pivot(index="d50", columns="run", values="ec_share").round(3))
