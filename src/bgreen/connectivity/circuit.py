"""Pinch points (circuit theory, McRae et al. 2008; as in Linkage Mapper's Pinchpoint Mapper).

For one link, 1 A is injected into patch i and patch j is grounded; the landscape is a resistor
network (8 neighbours, conductance = 1 / mean resistance / step length). Only the corridor is
kept: pixels whose cost distance from i plus from j stays within `width` of the least-cost
distance. The current through a pixel is the share of the whole flow that passes there, so a
value near 1 means the corridor is squeezed into one 10 m cell."""
from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from skimage.graph import MCP_Geometric

from bgreen.connectivity.graph import DIRS


def _cwd(R, sources):
    m = MCP_Geometric(np.where(np.isfinite(R), R, -1), fully_connected=True)
    c, _ = m.find_costs(np.argwhere(sources))
    return c


def corridor_current(R, labels, i, j, path_rc, res=10.0, width=2000.0, margin_px=150, max_px=600_000):
    """Return (r0, c0, current array, corridor mask, lcd) for the window around one link."""
    rr, cc = path_rc[:, 0], path_rc[:, 1]
    H, W = labels.shape
    r0, r1 = max(rr.min() - margin_px, 0), min(rr.max() + margin_px + 1, H)
    c0, c1 = max(cc.min() - margin_px, 0), min(cc.max() + margin_px + 1, W)
    Rw = R[r0:r1, c0:c1].astype(np.float64)
    Lw = labels[r0:r1, c0:c1]
    si, sj = Lw == i, Lw == j
    ci = _cwd(Rw, si) * res
    cj = _cwd(Rw, sj) * res
    tot = ci + cj
    lcd = float(np.nanmin(tot))
    corr = (tot <= lcd + width) | si | sj
    if corr.sum() > max_px:  # tighten the corridor rather than solve a huge system
        thr = np.quantile(tot[corr & ~si & ~sj], max_px / corr.sum())
        corr = (tot <= thr) | si | sj
    h, w = Rw.shape
    node = -np.ones((h, w), dtype=np.int64)
    free = corr & ~si & ~sj
    node[free] = np.arange(free.sum())
    SRC, GND = free.sum(), free.sum() + 1
    node[si], node[sj] = SRC, GND
    rows, cols, vals = [], [], []
    for dr, dc, dist in DIRS:
        a0r, a1r = 0, h - dr
        a0c, a1c = max(0, -dc), w - max(0, dc)
        na = node[a0r:a1r, a0c:a1c]
        nb = node[a0r + dr:a1r + dr, a0c + dc:a1c + dc]
        ok = (na >= 0) & (nb >= 0) & (na != nb)
        g = 1.0 / ((Rw[a0r:a1r, a0c:a1c][ok] + Rw[a0r + dr:a1r + dr, a0c + dc:a1c + dc][ok]) / 2.0 * dist)
        rows.append(na[ok]); cols.append(nb[ok]); vals.append(g)
    rows, cols, vals = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    N = GND + 1
    G = coo_matrix((np.r_[vals, vals], (np.r_[rows, cols], np.r_[cols, rows])), shape=(N, N)).tocsr()
    deg = np.asarray(G.sum(axis=1)).ravel()
    L = (coo_matrix((deg, (np.arange(N), np.arange(N))), shape=(N, N)) - G).tocsr()
    keep = np.arange(N - 1)  # drop the ground node
    b = np.zeros(N - 1)
    b[SRC] = 1.0
    v = np.zeros(N)
    v[:-1] = spsolve(L[keep][:, keep].tocsc(), b)
    # node current = half the sum of absolute branch currents
    cur = np.zeros(N)
    branch = np.abs(vals * (v[rows] - v[cols]))
    np.add.at(cur, rows, branch)
    np.add.at(cur, cols, branch)
    cur /= 2.0
    out = np.zeros((h, w), dtype=np.float32)
    out[free] = cur[node[free]]
    return r0, c0, out, corr, lcd
