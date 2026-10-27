import numpy as np

from bgreen.measures.access import two_step_fca


def test_2sfca_conserves_supply():
    # all supply ends up with someone: sum(pop * A) == supply reachable by anyone
    rng = np.random.default_rng(0)
    pop = rng.integers(0, 50, (60, 60)).astype(float)
    green = np.zeros((60, 60))
    green[20:25, 30:40] = 2500.0
    A = two_step_fca(green, pop, 300, 50)
    assert abs((A * pop).sum() - green.sum()) / green.sum() < 1e-6
