"""Cost model for expected-loss decisioning.

Every constant here is an assumption with a plausible range, registered in
ASSUMPTIONS.md and swept in the sensitivity analysis. Costs are expressed in
transaction minor units so that expected losses across actions are comparable.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..twin.schema import Action


@dataclass(frozen=True)
class CostModel:
    # Fraction of value lost when a fraudulent payment settles.
    loss_given_fraud: float = 1.0
    # Goodwill/value fraction lost when a legitimate payment is blocked outright.
    false_positive_value_frac: float = 0.15
    # Friction cost of a step-up, as a fraction of value, borne by good traffic.
    friction_frac: float = 0.010
    # Fraction of good customers who abandon after a step-up.
    legit_abandon_prob: float = 0.04
    # Cost of a hold, as a fraction of value.
    hold_frac: float = 0.015
    # Fixed operational cost of a manual review, in minor units.
    review_cost_minor: float = 300.0
    # Soft-warn friction, as a fraction of value.
    soft_warn_frac: float = 0.002

    # Effectiveness: probability the action blocks a fraud attempt.
    block_prob_step_up: float = 0.60
    block_prob_soft_warn: float = 0.20
    block_prob_hold: float = 0.50
    block_prob_manual_review: float = 0.85
    block_prob_decline: float = 1.0


def expected_losses(p: float, value_minor: float, cost: CostModel) -> dict[Action, float]:
    """Expected loss (minor units) for each action given fraud probability ``p``."""
    v = float(value_minor)
    lgf = cost.loss_given_fraud
    losses: dict[Action, float] = {}

    losses[Action.APPROVE] = p * v * lgf

    losses[Action.DECLINE] = (1 - p) * v * cost.false_positive_value_frac

    losses[Action.STEP_UP_3DS] = (
        p * (1 - cost.block_prob_step_up) * v * lgf
        + (1 - p) * v * cost.friction_frac
        + (1 - p) * cost.legit_abandon_prob * v * cost.false_positive_value_frac
    )

    losses[Action.SOFT_WARN] = (
        p * (1 - cost.block_prob_soft_warn) * v * lgf + (1 - p) * v * cost.soft_warn_frac
    )

    losses[Action.DELAY_HOLD] = (
        p * (1 - cost.block_prob_hold) * v * lgf + (1 - p) * v * cost.hold_frac
    )

    losses[Action.MANUAL_REVIEW] = (
        p * (1 - cost.block_prob_manual_review) * v * lgf + cost.review_cost_minor
    )

    return losses
