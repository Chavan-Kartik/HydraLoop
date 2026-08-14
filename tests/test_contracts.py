from hydraloop.twin.decision import (
    AlwaysApprove,
    BudgetState,
    DecisionContext,
    RiskDecisionEngine,
)
from hydraloop.twin.schema import Action, AuthRequest, Channel


def _ctx() -> DecisionContext:
    ar = AuthRequest(
        txn_id="t1",
        session_id="s1",
        ts=100.0,
        cardholder_id="c1",
        device_id="d1",
        merchant_id="m1",
        payee_id="p1",
        channel=Channel.A2A,
        amount_minor=5000,
        mcc=5411,
    )
    budget = BudgetState(
        day_index=0,
        step_ups_today=0,
        step_up_budget=10,
        reviews_today=0,
        review_capacity=400,
    )
    return DecisionContext(as_of=100.0, auth_request=ar, features={}, budget_state=budget)


def test_always_approve_satisfies_protocol():
    engine = AlwaysApprove()
    assert isinstance(engine, RiskDecisionEngine)


def test_always_approve_returns_approve():
    d = AlwaysApprove().decide(_ctx())
    assert d.action is Action.APPROVE
    assert d.risk_score == 0.0


def test_budget_exhaustion_flags():
    b = BudgetState(0, 10, 10, 400, 400)
    assert b.step_up_exhausted
    assert b.review_exhausted
