"""The cost-sensitive decision policy.

A risk score is not a decision. The policy converts a calibrated fraud
probability into one of six actions by minimising expected loss, then throttles
that choice to stay inside the friction and review budgets, spilling overflow to
an auto-decision and logging it.
"""

from __future__ import annotations

from collections.abc import Callable

from ..twin.decision import Decision, DecisionContext, ReasonCode
from ..twin.schema import Action
from .costs import CostModel, expected_losses
from .operating_point import OperatingPoint, calibrate_operating_point
from .serving import ScoringService


class PolicyEngine:
    def __init__(
        self,
        scorer: Callable[[dict], float],
        cost: CostModel | None = None,
        operating_point: OperatingPoint | None = None,
        latency_budget_ms: float = 150.0,
        fallback_scorer: Callable[[dict], float] | None = None,
    ) -> None:
        self.cost = cost or CostModel()
        self.op = operating_point or OperatingPoint()
        self.serving = ScoringService(scorer, fallback_scorer, latency_budget_ms)

    def _best_excluding(self, losses: dict[Action, float], excluded: set[Action]) -> Action:
        allowed = {a: v for a, v in losses.items() if a not in excluded}
        return min(allowed, key=allowed.get)

    def decide(self, ctx: DecisionContext) -> Decision:
        res = self.serving.score(dict(ctx.features))
        p = res.prob
        v = float(ctx.auth_request.amount_minor)
        losses = expected_losses(p, v, self.cost)
        action = min(losses, key=losses.get)
        notes: list[str] = []

        budget = ctx.budget_state
        if action == Action.STEP_UP_3DS:
            if p < self.op.step_up_min_p:
                action = Action.SOFT_WARN
                notes.append("step-up throttled below operating-point band")
            elif budget.step_up_exhausted:
                action = Action.SOFT_WARN
                notes.append("step-up budget exhausted for the day")

        if action == Action.MANUAL_REVIEW and (budget.review_exhausted or p < self.op.review_min_p):
            # Overflow: fall back to the best auto-decision (no human in the loop).
            action = self._best_excluding(losses, {Action.MANUAL_REVIEW})
            notes.append("review capacity exhausted; spilled to auto-decision")

        rationale = (
            f"p(fraud)={p:.3f}; chose {action.value} by expected-loss minimisation"
            + ("; " + "; ".join(notes) if notes else "")
        )
        reason = (ReasonCode(code="risk_probability", contribution=p),)
        return Decision(
            action=action,
            risk_score=p,
            rationale=rationale,
            reason_codes=reason,
            latency_ms=res.latency_ms,
            degraded=res.degraded,
        )


def build_policy_engine(cfg, detector, val_df) -> PolicyEngine:
    """Calibrate the operating point on validation data and wire the policy."""
    cost = CostModel()
    scores = detector.score(val_df) if len(val_df) else None
    if scores is not None and len(scores):
        values = val_df["amount_minor"].astype(float).to_numpy()
        daily_volume = max(
            1.0,
            cfg.simulation.legitimate_transactions_per_generation / max(1, cfg.simulation.horizon_days),
        )
        review_rate = min(0.5, cfg.defender.daily_review_capacity / daily_volume)
        op = calibrate_operating_point(
            scores, values, cost, cfg.defender.step_up_budget_rate, review_rate
        )
    else:
        op = OperatingPoint()

    return PolicyEngine(
        scorer=detector.score_row,
        cost=cost,
        operating_point=op,
        latency_budget_ms=cfg.defender.latency_budget_ms,
    )
