from hydraloop.blue.costs import CostModel, expected_losses
from hydraloop.twin.schema import Action


def test_low_risk_prefers_approve():
    losses = expected_losses(p=0.001, value_minor=10000, cost=CostModel())
    assert min(losses, key=losses.get) == Action.APPROVE


def test_high_risk_prefers_blocking_action():
    losses = expected_losses(p=0.95, value_minor=100000, cost=CostModel())
    best = min(losses, key=losses.get)
    assert best in {Action.DECLINE, Action.MANUAL_REVIEW, Action.STEP_UP_3DS, Action.DELAY_HOLD}
    assert best != Action.APPROVE


def test_approve_loss_scales_with_probability():
    lo = expected_losses(0.01, 10000, CostModel())[Action.APPROVE]
    hi = expected_losses(0.5, 10000, CostModel())[Action.APPROVE]
    assert hi > lo
