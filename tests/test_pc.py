import itertools

import numpy as np
import pandas as pd
import pytest

from bgreen.connectivity import pc


def brute_I(n, links, a, d50):
    """Best path probabilities by exhaustive Floyd-Warshall on products of p_ij."""
    k = np.log(2) / d50
    P = np.eye(n)
    for i, j, c in links:
        P[i, j] = P[j, i] = max(P[i, j], np.exp(-k * c))
    for m in range(n):
        P = np.maximum(P, np.outer(P[:, m], P[m, :]))
    return a @ P @ a


def make(links):
    return pd.DataFrame(links, columns=["i", "j", "cost"])


def test_ec_limits():
    a = np.array([4.0, 9.0, 1.0])
    A = pc.adjacency(3, make([(1, 2, 1e-9), (2, 3, 1e-9)]))
    D = pc.apsp(A)
    assert pc.ec(D, a, 1000) == pytest.approx(a.sum(), rel=1e-6)
    A = pc.adjacency(3, make([(1, 2, 1e9), (2, 3, 1e9)]))
    D = pc.apsp(A)
    assert pc.ec(D, a, 1000) == pytest.approx(np.sqrt((a ** 2).sum()), rel=1e-6)


def test_matches_brute_force_and_decomposition():
    rng = np.random.default_rng(1)
    n = 9
    pairs = [(i, j) for i, j in itertools.combinations(range(n), 2) if rng.random() < 0.45]
    links = [(i + 1, j + 1, float(rng.uniform(100, 3000))) for i, j in pairs]
    a = rng.uniform(1, 50, n)
    A = pc.adjacency(n, make(links))
    D = pc.apsp(A)
    zero_based = [(i - 1, j - 1, c) for i, j, c in links]
    for d50 in (300, 1000):
        assert pc.I_value(D, a, d50) == pytest.approx(brute_I(n, zero_based, a, d50), rel=1e-9)
    imp = pc.node_importance(A, a, [1000], workers=1)
    I = pc.I_value(D, a, 1000)
    for k in range(n):
        keep = [x for x in range(n) if x != k]
        sub = [(keep.index(i), keep.index(j), c) for i, j, c in zero_based if i != k and j != k]
        I_minus = brute_I(n - 1, sub, a[keep], 1000)
        assert imp.loc[k, "dPC_1000"] == pytest.approx(100 * (I - I_minus) / I, rel=1e-8)
        parts = imp.loc[k, ["intra_1000", "flux_1000", "connector_1000"]].sum()
        assert parts == pytest.approx(imp.loc[k, "dPC_1000"], rel=1e-8)


def test_stepping_stone_is_a_connector():
    # two big patches far apart, a tiny patch in the middle carries all the flow
    a = np.array([100.0, 0.5, 100.0])
    A = pc.adjacency(3, make([(1, 2, 500), (2, 3, 500), (1, 3, 5000)]))
    imp = pc.node_importance(A, a, [1000], workers=1)
    assert imp.loc[1, "connector_1000"] > 10 * imp.loc[1, "intra_1000"] + imp.loc[1, "flux_1000"]
    inter, used = pc.on_some_best_path(A)
    assert list(inter) == [1]
