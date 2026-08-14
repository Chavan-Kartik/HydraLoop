import pandas as pd

from hydraloop.red.economics import (
    NEVER_TRANSACT_PENALTY,
    AttackOutcome,
    ResourceUnitCosts,
    fitness,
    outcome_from_transactions,
)
from hydraloop.red.ledger import ResourceLedger


def test_never_transact_is_rejected():
    idle = AttackOutcome(n_attempts=0, value_settled=0.0, resource_cost=0.0,
                         time_to_cashout_h=0.0, detection_events=0, friction_events=0)
    assert fitness(idle) == NEVER_TRANSACT_PENALTY
    # A lossy but active campaign must still beat doing nothing.
    active = AttackOutcome(1, 100.0, 50.0, 5.0, 2, 1)
    assert fitness(active) > fitness(idle)


def test_detection_and_friction_reduce_fitness():
    base = AttackOutcome(10, 100000.0, 1000.0, 5.0, 0, 0)
    caught = AttackOutcome(10, 100000.0, 1000.0, 5.0, 3, 0)
    frictioned = AttackOutcome(10, 100000.0, 1000.0, 5.0, 0, 3)
    assert fitness(caught) < fitness(base)
    assert fitness(frictioned) < fitness(base)


def test_roi_and_outcome_extraction():
    tx = pd.DataFrame(
        [
            {"is_fraud": True, "approved": True, "settled": True, "captured_minor": 5000,
             "charged_back": False, "action": "approve", "ts": 0.0, "settlement_ts": 3600.0},
            {"is_fraud": True, "approved": False, "settled": False, "captured_minor": 0,
             "charged_back": False, "action": "decline", "ts": 0.0, "settlement_ts": None},
            {"is_fraud": True, "approved": True, "settled": True, "captured_minor": 2000,
             "charged_back": True, "action": "step_up_3ds", "ts": 0.0, "settlement_ts": 7200.0},
        ]
    )
    ledger = ResourceLedger()
    ledger.allocate("e1", "mule_accounts", 2, 10)
    out = outcome_from_transactions(tx, ledger, ResourceUnitCosts())
    assert out.n_attempts == 3
    assert out.value_settled == 7000.0
    assert out.detection_events == 2  # one decline + one chargeback
    assert out.friction_events == 1
    assert out.resource_cost == 2 * ResourceUnitCosts().mule_accounts
    assert out.roi == 7000.0 / (2 * 5000.0)
