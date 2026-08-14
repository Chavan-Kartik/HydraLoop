"""Gate G2: policy actions change the world.

The defence policy is live inside the twin, so a step-up genuinely reduces an
attacker's success. This is what makes the loop an adversarial environment
rather than a retrain script.
"""

from __future__ import annotations

from hydraloop.red.dsl import genome_from_template
from hydraloop.red.mixer import build_attack_specs
from hydraloop.twin.decision import Decision
from hydraloop.twin.population import SECONDS_PER_DAY
from hydraloop.twin.run import build_engine, legit_session_specs
from hydraloop.twin.schema import Action


class _StepUpEverything:
    def decide(self, ctx) -> Decision:
        return Decision(action=Action.STEP_UP_3DS, risk_score=1.0, rationale="force step-up")


class _ApproveEverything:
    def decide(self, ctx) -> Decision:
        return Decision(action=Action.APPROVE, risk_score=0.0, rationale="approve")


def _settled_fraud_value(small_config, engine_decision) -> int:
    engine, registry = build_engine(small_config)
    horizon_s = small_config.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(small_config, engine, registry, 300)
    genome = genome_from_template("social_engineering", "AF-09", {})
    fraud, _ = build_attack_specs(engine, registry, [genome], 60, horizon_s)
    engine.decision = engine_decision
    result = engine.simulate(legit + fraud)
    return sum(
        t["captured_minor"]
        for t in result.transactions
        if t["is_fraud"] and t["approved"]
    )


def test_step_up_reduces_attacker_success(small_config):
    approved_value = _settled_fraud_value(small_config, _ApproveEverything())
    stepped_value = _settled_fraud_value(small_config, _StepUpEverything())
    assert approved_value > 0
    # Forcing step-ups strictly reduces the fraudulent value that gets through.
    assert stepped_value < approved_value
