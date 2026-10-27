"""Current maps for the most important links of a network (Pinchpoint Mapper style).
Usage: python scripts/run_pinchpoints.py [run] [top]"""
import sys
import time

import numpy as np
import pandas as pd
from pyproj import Transformer

from bgreen.config import INTERIM
from bgreen.connectivity import circuit, graph
from bgreen.grid import URBAN

if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "main"
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    d = INTERIM / f"conn_{run}"
    labels = np.load(d / "labels.npy")
    R = np.load(d / "resistance.npy").astype("float64")
    ext = np.load(d / "ext_mask.npy") if (d / "ext_mask.npy").exists() else np.load(INTERIM / "ext_mask.npy")
    R = np.where(ext, R, np.inf)
    alloc = graph.Allocation(cost=np.load(d / "alloc_cost.npy"), zone=np.load(d / "alloc_zone.npy"),
                             pred=np.load(d / "alloc_pred.npy"), res=URBAN.res)
    links = pd.read_parquet(d / "links.parquet")
    limp = pd.read_parquet(d / "link_importance.parquet").sort_values("dLink_1000", ascending=False).head(top)
    tr = Transformer.from_crs(URBAN.crs, "EPSG:4326", always_xy=True)
    W = URBAN.width
    mosaic = np.zeros(labels.shape, dtype=np.float32)
    rows = []
    for rank, lk in enumerate(limp.itertuples(), 1):
        i, j = int(lk.i), int(lk.j)
        row = links[(links.i == min(i, j)) & (links.j == max(i, j))].iloc[0]
        path = graph.link_path(alloc, int(row.pa), int(row.pb))
        rc = np.c_[np.array(path) // W, np.array(path) % W]
        t = time.time()
        r0, c0, cur, corr, lcd = circuit.corridor_current(R, labels, i, j, rc, res=URBAN.res, width=2000.0,
                                                          margin_px=250)
        h, w = cur.shape
        np.maximum(mosaic[r0:r0 + h, c0:c0 + w], cur, out=mosaic[r0:r0 + h, c0:c0 + w])
        np.savez_compressed(d / f"current_{i}_{j}.npz", r0=r0, c0=c0, cur=cur, corr=corr, lcd=lcd)
        np.save(d / f"path_{i}_{j}.npy", np.array(path, dtype=np.int64))
        k = np.unravel_index(np.argmax(cur), cur.shape)
        x = URBAN.left + (c0 + k[1] + 0.5) * URBAN.res
        y = URBAN.top - (r0 + k[0] + 0.5) * URBAN.res
        lon, lat = tr.transform(x, y)
        rows.append({"rank": rank, "i": i, "j": j, "dLink": lk.dLink_1000, "dLink_1000": lk.dLink_1000,
                     "lcd": lcd, "link_cost": float(row.cost), "path_len_m": len(path) * URBAN.res,
                     "corridor_px": int(corr.sum()), "peak_current": float(cur.max()), "peak_x": x, "peak_y": y,
                     "lon": lon, "lat": lat, "seconds": round(time.time() - t, 1)})
        print(rows[-1], flush=True)
    np.save(d / "current_mosaic.npy", mosaic)
    pd.DataFrame(rows).to_csv(d / "pinchpoints.csv", index=False)
