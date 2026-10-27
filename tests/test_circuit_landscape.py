import numpy as np

from bgreen.connectivity import circuit, landscape


def test_current_concentrates_in_a_gap():
    # two patches separated by a wall with a one-cell gap: all current must pass the gap
    R = np.ones((21, 21))
    labels = np.zeros((21, 21), dtype=np.int32)
    labels[:, :3] = 1
    labels[:, -3:] = 2
    R[:, 10] = 1e6
    R[10, 10] = 1.0
    path = np.array([[10, 3], [10, 17]])
    r0, c0, cur, corr, lcd = circuit.corridor_current(R, labels, 1, 2, path, res=10, width=1e9, margin_px=30)
    assert abs(cur[10 - r0, 10 - c0] - 1.0) < 1e-3
    # in an open landscape no cell carries the whole flow
    R2 = np.ones((21, 21))
    r0, c0, cur2, _, _ = circuit.corridor_current(R2, labels, 1, 2, path, res=10, width=1e9, margin_px=30)
    assert cur2.max() < 0.2


def test_class_metrics_simple():
    hab = np.zeros((10, 10), dtype=bool)
    hab[1:3, 1:3] = True      # 4 cells
    hab[6:9, 6:9] = True      # 9 cells
    m = landscape.class_metrics(hab, np.ones_like(hab), res=10)
    assert m["NP"] == 2
    assert abs(m["PLAND_pct"] - 13.0) < 1e-9
    assert abs(m["MESH_ha"] - ((0.04 ** 2 + 0.09 ** 2) / 1.0)) < 1e-12
    assert m["ENN_MN_m"] > 0
