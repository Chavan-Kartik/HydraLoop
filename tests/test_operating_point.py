import numpy as np

from hydraloop.blue.costs import CostModel
from hydraloop.blue.operating_point import calibrate_operating_point


def test_step_up_rate_throttled_to_budget():
    rng = np.random.default_rng(0)
    # A population with many mid-risk transactions that would all prefer step-up.
    scores = rng.uniform(0.2, 0.6, size=5000)
    values = rng.uniform(1000, 50000, size=5000)
    op = calibrate_operating_point(
        scores, values, CostModel(), step_up_budget_rate=0.02, review_capacity_rate=0.01
    )
    assert op.achieved_step_up_rate <= 0.02 + 1e-6
    if op.step_up_min_p > 0:
        assert "narrowed step-up band to the budgeted rate" in op.relaxations


def test_feasible_when_few_step_ups():
    scores = np.concatenate([np.full(4900, 0.001), np.full(100, 0.9)])
    values = np.full(5000, 10000.0)
    op = calibrate_operating_point(
        scores, values, CostModel(), step_up_budget_rate=0.5, review_capacity_rate=0.01
    )
    assert op.feasible


def test_empty_input_safe():
    op = calibrate_operating_point(
        np.array([]), np.array([]), CostModel(), 0.02, 0.01
    )
    assert op.step_up_min_p == 0.0
