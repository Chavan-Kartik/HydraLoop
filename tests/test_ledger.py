import pytest

from hydraloop.red.ledger import BudgetExhausted, ResourceLedger


def test_allocation_within_budget_balances():
    led = ResourceLedger()
    led.allocate("e1", "operator_hours", 0.5, budget=2.0)
    led.allocate("e1", "operator_hours", 0.5, budget=2.0)
    led.allocate("e1", "mule_accounts", 2, budget=3)
    assert led.balances()
    assert led.totals()["operator_hours"] == 1.0
    assert led.totals()["mule_accounts"] == 2.0


def test_over_budget_raises():
    led = ResourceLedger()
    led.allocate("e1", "devices", 3, budget=3)
    with pytest.raises(BudgetExhausted):
        led.allocate("e1", "devices", 1, budget=3)


def test_unknown_kind_rejected():
    led = ResourceLedger()
    with pytest.raises(ValueError):
        led.allocate("e1", "not_a_resource", 1, budget=1)
