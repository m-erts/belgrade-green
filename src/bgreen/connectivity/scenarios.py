"""'Build-over' scenarios: a patch becomes built-up land (resistance of class 50) and the whole
network is rebuilt from the raster, so other patches can re-link around the gap. This is the
honest version of the dPC removal test, which keeps the old planar links."""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from bgreen.connectivity import graph, pc
from bgreen.connectivity.resistance import LANDCOVER

D50S = [300, 1000, 3000]


def _ec_from(labels, areas, R, ext, res):
    alloc = graph.allocate(R, labels, ext, res)
    links = graph.zone_links(alloc, R)
    n = labels.max()
    D = pc.apsp(pc.adjacency(n, links))
    return {d: pc.ec(D, areas, d) for d in D50S}


def _one(args):
    run_dir, p, scenario = args
    d = Path(run_dir)
    labels = np.load(d / "labels.npy")
    areas = np.load(d / "areas.npy")
    R = np.load(d / "resistance.npy").astype("float64")
    ext = np.load(d / "ext_mask.npy") if (d / "ext_mask.npy").exists() else np.load(d.parent / "ext_mask.npy")
    m = labels == p
    R[m] = np.maximum(R[m], LANDCOVER[scenario][50])
    remap = np.zeros(labels.max() + 1, dtype=np.int32)
    keep = np.r_[0:p - 1, p:len(areas)]
    remap[keep + 1] = np.arange(1, len(keep) + 1)
    lab2 = remap[labels]
    ec = _ec_from(lab2, areas[keep], R, ext, 10.0)
    return p, ec


def build_over(run_dir: Path, patches, scenario="main", workers=3) -> pd.DataFrame:
    s = json.loads((run_dir / "summary.json").read_text())
    base = {int(k): v for k, v in s["ec_ha"].items()}
    areas = np.load(run_dir / "areas.npy")
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for p, ec in ex.map(_one, [(str(run_dir), int(p), scenario) for p in patches]):
            row = {"patch": p, "area_ha": float(areas[p - 1])}
            for d in D50S:
                row[f"EC_{d}"] = ec[d]
                row[f"EC_loss_{d}"] = base[d] - ec[d]
                row[f"EC_loss_pct_{d}"] = 100 * (base[d] - ec[d]) / base[d]
            row["leverage_1000"] = row["EC_loss_1000"] / row["area_ha"]
            rows.append(row)
            print(row, flush=True)
    return pd.DataFrame(rows)


def build_over_pixels(run_dir: Path, mask: np.ndarray, scenario="main", min_area_ha=1.0):
    """Turn arbitrary habitat pixels into built-up land, re-label patches and rebuild the network."""
    from bgreen.connectivity import patches
    from bgreen.grid import URBAN

    d = Path(run_dir)
    labels = np.load(d / "labels.npy")
    R = np.load(d / "resistance.npy").astype("float64")
    ext = np.load(d / "ext_mask.npy") if (d / "ext_mask.npy").exists() else np.load(d.parent / "ext_mask.npy")
    hab = (labels > 0) & ~mask
    R[mask] = np.maximum(R[mask], LANDCOVER[scenario][50])
    lab2, areas2 = patches.label_patches(hab, URBAN, min_area_ha)
    return _ec_from(lab2, areas2, R, ext, 10.0), areas2.sum()
