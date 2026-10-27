"""Planar patch graph (as in Graphab): one multi-source least-cost run from all patches splits
the landscape into cost zones; two patches are linked when their zones touch, and the link cost
is the cheapest path across that shared border."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage.graph import MCP_Geometric

DIRS = ((0, 1, 1.0), (1, 0, 1.0), (1, 1, np.sqrt(2)), (1, -1, np.sqrt(2)))


@dataclass
class Allocation:
    cost: np.ndarray        # cumulative least cost from the nearest patch, in metres x resistance
    zone: np.ndarray        # label of that patch (0 = unreachable)
    pred: np.ndarray        # flat index of the predecessor on the least-cost path (self for roots)
    res: float


def allocate(resistance: np.ndarray, labels: np.ndarray, passable: np.ndarray, res: float) -> Allocation:
    R = resistance.astype(np.float64)
    R = np.where(passable, R, -1.0)
    starts = np.argwhere(labels > 0)
    mcp = MCP_Geometric(R, fully_connected=True)
    cost, tb = mcp.find_costs(starts)
    H, W = labels.shape
    off = np.asarray(mcp.offsets).astype(np.int64)
    idx = np.arange(H * W, dtype=np.int64)
    tbf = tb.ravel()
    pred = idx.copy()
    ok = tbf >= 0
    o = off[tbf[ok]]
    pred[ok] = idx[ok] - (o[:, 0] * W + o[:, 1])
    root = pred.copy()
    for _ in range(64):
        nxt = root[root]
        if np.array_equal(nxt, root):
            break
        root = nxt
    zone = labels.ravel()[root].reshape(H, W)
    zone[tb == -2] = 0
    cost = np.where(np.isfinite(cost), cost * res, np.inf)
    return Allocation(cost=cost, zone=zone, pred=pred, res=res)


def zone_links(alloc: Allocation, resistance: np.ndarray) -> pd.DataFrame:
    """Least-cost link between every pair of touching zones, with the meeting pixels."""
    H, W = alloc.zone.shape
    parts = []
    for dr, dc, dist in DIRS:
        r0, r1 = (0, H - dr)
        c0, c1 = (max(0, -dc), W - max(0, dc))
        a = alloc.zone[r0:r1, c0:c1]
        b = alloc.zone[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
        m = (a > 0) & (b > 0) & (a != b)
        if not m.any():
            continue
        rr, cc = np.nonzero(m)
        ra, ca = rr + r0, cc + c0
        rb, cb = ra + dr, ca + dc
        step = (resistance[ra, ca] + resistance[rb, cb]) / 2.0 * dist * alloc.res
        tot = alloc.cost[ra, ca] + alloc.cost[rb, cb] + step
        za, zb = a[m], b[m]
        swap = za > zb
        i = np.where(swap, zb, za)
        j = np.where(swap, za, zb)
        pa = np.where(swap, rb * W + cb, ra * W + ca)
        pb = np.where(swap, ra * W + ca, rb * W + cb)
        parts.append(pd.DataFrame({"i": i, "j": j, "cost": tot, "pa": pa, "pb": pb}))
    df = pd.concat(parts, ignore_index=True)
    df = df.loc[df.groupby(["i", "j"])["cost"].idxmin()].reset_index(drop=True)
    return df


def euclidean_links(labels: np.ndarray, passable: np.ndarray, res: float) -> pd.DataFrame:
    """Edge-to-edge Euclidean distance between neighbouring patches (Euclidean Voronoi)."""
    dist, (ir, ic) = ndi.distance_transform_edt(labels == 0, return_indices=True)
    zone = labels[ir, ic]
    zone = np.where(passable | (labels > 0), zone, 0)
    H, W = labels.shape
    parts = []
    for dr, dc, step in DIRS:
        r0, r1 = (0, H - dr)
        c0, c1 = (max(0, -dc), W - max(0, dc))
        a = zone[r0:r1, c0:c1]
        b = zone[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
        m = (a > 0) & (b > 0) & (a != b)
        if not m.any():
            continue
        da = dist[r0:r1, c0:c1][m]
        db = dist[r0 + dr:r1 + dr, c0 + dc:c1 + dc][m]
        za, zb = a[m], b[m]
        parts.append(pd.DataFrame({"i": np.minimum(za, zb), "j": np.maximum(za, zb),
                                   "dist": (da + db + step - 1.0).clip(min=0) * res}))
    df = pd.concat(parts, ignore_index=True)
    return df.groupby(["i", "j"], as_index=False)["dist"].min()


def trace(alloc: Allocation, start: int, max_steps: int = 100000) -> list[int]:
    """Flat pixel indices from `start` back to the patch it was reached from."""
    path = [start]
    p = start
    for _ in range(max_steps):
        q = alloc.pred[p]
        if q == p:
            break
        path.append(q)
        p = q
    return path


def link_path(alloc: Allocation, pa: int, pb: int) -> list[int]:
    return trace(alloc, pa)[::-1] + trace(alloc, pb)
