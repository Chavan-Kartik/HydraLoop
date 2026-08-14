import numpy as np

from hydraloop.red.dsl import default_genome, genome_from_dict
from hydraloop.red.interpreter import interpret_episode
from hydraloop.red.ledger import ResourceLedger
from hydraloop.twin.entities import Cardholder


def _holder() -> Cardholder:
    return Cardholder(
        cardholder_id="c1",
        created_ts=0.0,
        home_geo=1,
        age_band="45_54",
        balance_minor=100000,
        limit_minor=200000,
        activity_rate_per_day=1.0,
        diurnal_peak_hour=13.0,
        mcc_weights={5411: 1.0},
        device_ids=["d1"],
        payee_ids=["p1"],
        channel_weights={"a2a": 1.0},
    )


def test_episode_produces_fraud_specs():
    g = default_genome(attack_id="AF-09")
    led = ResourceLedger()
    specs = interpret_episode(g, _holder(), 100.0, np.random.default_rng(0), led, "AF-09-0")
    assert specs
    assert all(s.is_fraud for s in specs)
    assert all(s.genome_id == g.genome_id for s in specs)
    assert led.balances()


def test_budget_exhaustion_aborts_episode():
    d = default_genome(attack_id="AF-09").to_dict()
    d["genes"]["amount_policy"]["steps"] = [0.1, 0.2, 0.3, 0.4, 0.5]
    # Only enough operator budget for a single transaction.
    d["genes"]["resource_budget"]["operator_hours"] = 0.15
    g = genome_from_dict(d)
    led = ResourceLedger()
    specs = interpret_episode(g, _holder(), 0.0, np.random.default_rng(1), led, "AF-09-x")
    assert len(specs) < 5  # aborted early
    assert led.spent("AF-09-x", "operator_hours") <= 0.15 + 1e-9
    assert led.balances()


def test_amount_scales_with_base():
    d = default_genome(attack_id="AF-09").to_dict()
    d["genes"]["amount_policy"] = {"type": "flat", "base": "balance", "steps": [0.5], "max_fraction": 0.5}
    g = genome_from_dict(d)
    led = ResourceLedger()
    specs = interpret_episode(g, _holder(), 0.0, np.random.default_rng(2), led, "e")
    ladder = [s for s in specs if s.amount_minor is not None]
    assert any(s.amount_minor == 50000 for s in ladder)  # 0.5 * balance 100000
