"""Attacker economics: the fitness the red-team search actually optimises.

An attacker is a business. Fitness rewards value that settles and penalises the
resources burned, the time to cash out, the detection events triggered, and the
friction encountered. A hard guard rejects the degenerate "never transact"
optimum: an attacker that does nothing spends nothing and would otherwise score
zero, which must never beat a genuine (if lossy) campaign.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..twin.decision import RiskDecisionEngine
from ..twin.population import SECONDS_PER_DAY
from ..twin.run import build_engine
from .dsl.genome import Genome
from .ledger import RESOURCE_KINDS, ResourceLedger
from .mixer import build_attack_specs

NEVER_TRANSACT_PENALTY = -1e9


@dataclass(frozen=True)
class FitnessWeights:
    value: float = 1.0
    resource: float = 1.0
    time: float = 200.0
    detection: float = 30000.0
    friction: float = 8000.0


@dataclass(frozen=True)
class ResourceUnitCosts:
    mule_accounts: float = 5000.0
    synthetic_identities: float = 8000.0
    devices: float = 1500.0
    operator_hours: float = 4000.0

    def total(self, totals: dict[str, float]) -> float:
        unit = {
            "mule_accounts": self.mule_accounts,
            "synthetic_identities": self.synthetic_identities,
            "devices": self.devices,
            "operator_hours": self.operator_hours,
        }
        return float(sum(unit[k] * totals.get(k, 0.0) for k in RESOURCE_KINDS))


@dataclass(frozen=True)
class AttackOutcome:
    n_attempts: int
    value_settled: float
    resource_cost: float
    time_to_cashout_h: float
    detection_events: int
    friction_events: int

    @property
    def roi(self) -> float:
        return self.value_settled / max(1.0, self.resource_cost)


def outcome_from_transactions(tx: pd.DataFrame, ledger: ResourceLedger,
                              costs: ResourceUnitCosts) -> AttackOutcome:
    fraud = tx[tx["is_fraud"]]
    n = int(len(fraud))
    settled = fraud[(fraud["approved"]) & (fraud["settled"])]
    value = float(settled["captured_minor"].sum())
    blocked = int((~fraud["approved"]).sum())
    charged_back = int(fraud["charged_back"].sum())
    friction = int((fraud["action"] == "step_up_3ds").sum())
    if len(settled):
        cashout_h = float(((settled["settlement_ts"] - settled["ts"]) / 3600.0).mean())
    else:
        cashout_h = 0.0
    return AttackOutcome(
        n_attempts=n,
        value_settled=value,
        resource_cost=costs.total(ledger.totals()),
        time_to_cashout_h=cashout_h,
        detection_events=blocked + charged_back,
        friction_events=friction,
    )


def fitness(outcome: AttackOutcome, weights: FitnessWeights | None = None) -> float:
    weights = weights or FitnessWeights()
    if outcome.n_attempts == 0:
        return NEVER_TRANSACT_PENALTY
    return (
        weights.value * outcome.value_settled
        - weights.resource * outcome.resource_cost
        - weights.time * outcome.time_to_cashout_h
        - weights.detection * outcome.detection_events
        - weights.friction * outcome.friction_events
    )


def evaluate_genome(
    cfg,
    genome: Genome,
    decision_engine: RiskDecisionEngine | None,
    n_episodes: int = 60,
    costs: ResourceUnitCosts | None = None,
) -> tuple[AttackOutcome, pd.DataFrame]:
    """Run one genome against the live policy and score its economics."""
    costs = costs or ResourceUnitCosts()
    engine, registry = build_engine(cfg)
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    specs, ledger = build_attack_specs(engine, registry, [genome], n_episodes, horizon_s)
    if decision_engine is not None:
        engine.decision = decision_engine
    tx = pd.DataFrame(engine.simulate(specs).transactions)
    if tx.empty:
        return AttackOutcome(0, 0.0, 0.0, 0.0, 0, 0), tx
    return outcome_from_transactions(tx, ledger, costs), tx
