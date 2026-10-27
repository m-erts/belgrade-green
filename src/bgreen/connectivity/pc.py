"""Probability of Connectivity (Saura & Pascual-Hortal 2007), Equivalent Connected area
(Saura et al. 2011) and the dPC split into intra / flux / connector (Saura & Rubio 2010).

p_ij = exp(-k * d_ij) with k = ln 2 / d50, so a link as long as the median dispersal distance
is crossed with probability 0.5. The best (maximum-product) path between two patches is the
shortest path in link cost, hence p*_ij = exp(-k * D_ij) with D from all-pairs Dijkstra."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

LN2 = np.log(2.0)


def adjacency(n: int, links: pd.DataFrame) -> csr_matrix:
    """Undirected weighted adjacency on nodes 0..n-1 from a links table with i, j (1-based), cost."""
    i = links["i"].to_numpy() - 1
    j = links["j"].to_numpy() - 1
    w = links["cost"].to_numpy().astype(float)
    w = np.maximum(w, 1e-9)  # csgraph treats explicit zeros as missing edges
    return csr_matrix((np.r_[w, w], (np.r_[i, j], np.r_[j, i])), shape=(n, n))


def apsp(A: csr_matrix) -> np.ndarray:
    return dijkstra(A, directed=False)


def flux_matrix(D: np.ndarray, d50: float) -> np.ndarray:
    with np.errstate(over="ignore"):
        return np.exp(-(LN2 / d50) * D)


def I_value(D: np.ndarray, a: np.ndarray, d50: float) -> float:
    P = flux_matrix(D, d50)
    return float(a @ P @ a)


def ec(D: np.ndarray, a: np.ndarray, d50: float) -> float:
    """Equivalent Connected area, in the units of `a`."""
    return float(np.sqrt(I_value(D, a, d50)))


def _without_node(A: csr_matrix, k: int) -> csr_matrix:
    keep = np.r_[0:k, k + 1:A.shape[0]]
    return A[keep][:, keep]


def _removal_I(args):
    A, a, d50s, k = args
    D = apsp(_without_node(A, k))
    ak = np.delete(a, k)
    return k, [I_value(D, ak, d) for d in d50s]


def _edge_removal_I(args):
    A, a, d50s, (u, v) = args
    B = A.tolil(copy=True)
    B[u, v] = 0
    B[v, u] = 0
    B = B.tocsr()
    B.eliminate_zeros()
    D = apsp(B)
    return (u, v), [I_value(D, a, d) for d in d50s]


def node_importance(A: csr_matrix, a: np.ndarray, d50s, candidates=None, workers: int = 8) -> pd.DataFrame:
    """dPC and its three fractions for every node, in % of I (Saura & Rubio 2010)."""
    n = len(a)
    D = apsp(A)
    out = {"node": np.arange(n)}
    if candidates is None:
        candidates = np.arange(n)
    removal = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for k, vals in ex.map(_removal_I, [(A, a, d50s, int(k)) for k in candidates], chunksize=4):
            removal[k] = vals
    for t, d in enumerate(d50s):
        P = flux_matrix(D, d)
        I = float(a @ P @ a)
        intra = a ** 2
        flux = 2 * a * (P @ a - a)  # sum over j != k of a_k a_j p*_kj, both directions
        I_minus = I - intra - flux  # exact when the node lies on no best path between others
        for k, vals in removal.items():
            I_minus[k] = vals[t]
        dpc = 100 * (I - I_minus) / I
        out[f"dPC_{d:g}"] = dpc
        out[f"intra_{d:g}"] = 100 * intra / I
        out[f"flux_{d:g}"] = 100 * flux / I
        out[f"connector_{d:g}"] = np.clip(dpc - 100 * intra / I - 100 * flux / I, 0, None)
        out[f"EC_without_{d:g}"] = np.sqrt(np.clip(I_minus, 0, None))
    return pd.DataFrame(out)


def link_importance(A: csr_matrix, a: np.ndarray, d50s, edges, workers: int = 8) -> pd.DataFrame:
    """dLink: % drop of I when one link is removed (patches stay)."""
    D = apsp(A)
    base = [I_value(D, a, d) for d in d50s]
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for (u, v), vals in ex.map(_edge_removal_I, [(A, a, d50s, (int(u), int(v))) for u, v in edges],
                                   chunksize=4):
            row = {"u": u, "v": v}
            for t, d in enumerate(d50s):
                row[f"dLink_{d:g}"] = 100 * (base[t] - vals[t]) / base[t]
            rows.append(row)
    return pd.DataFrame(rows)


def on_some_best_path(A: csr_matrix):
    """Nodes that are an intermediate vertex of at least one best path, and edges used by one."""
    D, pred = dijkstra(A, directed=False, return_predecessors=True)
    n = A.shape[0]
    inter = np.zeros(n, dtype=bool)
    used = set()
    for s in range(n):
        p = pred[s]
        reach = np.flatnonzero(p >= 0)
        # every predecessor that is not the source is an intermediate node of some path from s
        q = p[reach]
        inter[q[q != s]] = True
        for t, u in zip(reach, q):
            used.add((min(t, u), max(t, u)))
    return np.flatnonzero(inter), sorted(used)
