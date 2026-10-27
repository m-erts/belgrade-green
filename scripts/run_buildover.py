"""Rebuild the network without each of the strongest connector candidates."""
import sys

import numpy as np
import pandas as pd

from bgreen.config import INTERIM
from bgreen.connectivity.scenarios import build_over

if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "main"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    d = INTERIM / f"conn_{run}"
    imp = pd.read_parquet(d / "node_importance.parquet")
    imp["share"] = imp.connector_1000 / imp.dPC_1000.replace(0, np.nan)
    cand = pd.concat([imp.sort_values("connector_1000", ascending=False).head(n),
                      imp[imp.area_ha < 50].sort_values("dPC_1000", ascending=False).head(n // 2)]).drop_duplicates("patch")
    out = build_over(d, cand.patch.tolist())
    out = out.merge(imp[["patch", "dPC_1000", "connector_1000", "EC_without_1000"]], on="patch")
    out.to_parquet(d / "buildover.parquet")
    print(out.sort_values("EC_loss_1000", ascending=False).round(2).to_string(index=False))
