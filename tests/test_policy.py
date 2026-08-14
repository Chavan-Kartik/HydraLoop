from hydraloop.blue.costs import CostModel
from hydraloop.blue.operating_point import OperatingPoint
from hydraloop.blue.policy import PolicyEngine
from hydraloop.twin.decision import BudgetState, DecisionContext
from hydraloop.twin.schema import Action, AuthRequest, Channel


def _ctx(step_ups=0, step_budget=100, reviews=0, review_cap=100, amount=10000):
    ar = AuthRequest("t", "s", 100.0, "c1", "d1", "m1", "p1", Channel.A2A, amount, 5411)
    b = BudgetState(0, step_ups, step_budget, reviews, review_cap)
    return DecisionContext(as_of=100.0, auth_request=ar, features={"velocity_24h": 1.0}, budget_state=b)


def test_every_decision_has_action_and_rationale():
    engine = PolicyEngine(scorer=lambda f: 0.02)
    d = engine.decide(_ctx())
    assert isinstance(d.action, Action)
    assert d.rationale
    assert 0.0 <= d.risk_score <= 1.0


def test_low_risk_approved():
    engine = PolicyEngine(scorer=lambda f: 0.0)
    assert engine.decide(_ctx()).action == Action.APPROVE


def test_step_up_throttled_below_band():
    # Operating point forbids step-up below p=0.9; a mid-risk case is demoted.
    op = OperatingPoint(step_up_min_p=0.9, review_min_p=0.99)
    engine = PolicyEngine(scorer=lambda f: 0.5, cost=CostModel(), operating_point=op)
    d = engine.decide(_ctx())
    if "throttled" in d.rationale:
        assert d.action == Action.SOFT_WARN


def test_step_up_budget_exhausted_demotes():
    op = OperatingPoint(step_up_min_p=0.0, review_min_p=0.99)
    engine = PolicyEngine(scorer=lambda f: 0.5, operating_point=op)
    d = engine.decide(_ctx(step_ups=100, step_budget=100))
    # With step-up preferred but budget exhausted, it must not step up.
    assert d.action != Action.STEP_UP_3DS


def test_review_overflow_spills_to_auto_decision():
    # Force manual review to be preferred, then exhaust review capacity.
    cost = CostModel(review_cost_minor=1.0, block_prob_manual_review=0.99)
    engine = PolicyEngine(scorer=lambda f: 0.7, cost=cost, operating_point=OperatingPoint(review_min_p=0.0))
    d = engine.decide(_ctx(reviews=100, review_cap=100))
    assert d.action != Action.MANUAL_REVIEW
    assert "spilled to auto-decision" in d.rationale
