"""Constrained operating-point selection.

The expected-loss argmin defines *what* we would do per transaction. This module
throttles those choices so aggregate friction and review load stay within budget.
If the constraints cannot all be met, it relaxes them in a documented priority
order rather than silently picking something:

  1. Narrow the step-up band (only step up the highest-probability cases).
  2. Convert the demoted step-ups to soft-warn (cheaper friction).
  3. If still infeasible, report infeasible and keep the least-loss feasible mix.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..twin.schema import Action
from .costs import CostModel, expected_losses


@dataclass(frozen=True)
class OperatingPoint:
    step_up_min_p: float = 0.0
    review_min_p: float = 0.5
    feasible: bool = True
    achieved_step_up_rate: float = 0.0
    relaxations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "step_up_min_p": self.step_up_min_p,
            "review_min_p": self.review_min_p,
            "feasible": self.feasible,
            "achieved_step_up_rate": self.achieved_step_up_rate,
            "relaxations": list(self.relaxations),
        }


def _preferred_action(p: float, v: float, cost: CostModel) -> Action:
    losses = expected_losses(p, v, cost)
    return min(losses, key=losses.get)


def calibrate_operating_point(
    scores: np.ndarray,
    values: np.ndarray,
    cost: CostModel,
    step_up_budget_rate: float,
    review_capacity_rate: float,
) -> OperatingPoint:
    prefs = np.array(
        [_preferred_action(float(p), float(v), cost) for p, v in zip(scores, values, strict=True)]
    )
    n = len(scores)
    if n == 0:
        return OperatingPoint()

    step_up_mask = prefs == Action.STEP_UP_3DS
    step_up_rate = float(step_up_mask.mean())
    relaxations: list[str] = []
    step_up_min_p = 0.0
    feasible = True

    if step_up_rate > step_up_budget_rate:
        # Keep only the highest-probability step-ups up to the budgeted rate.
        step_scores = scores[step_up_mask]
        keep_fraction = step_up_budget_rate / step_up_rate
        step_up_min_p = float(np.quantile(step_scores, 1.0 - keep_fraction))
        relaxations.append("narrowed step-up band to the budgeted rate")
        relaxations.append("demoted sub-threshold step-ups to soft-warn")
        achieved = float((step_up_mask & (scores >= step_up_min_p)).mean())
        if achieved > step_up_budget_rate + 1e-6:
            feasible = False
            relaxations.append("residual step-up rate still above budget; reported infeasible")
    else:
        achieved = step_up_rate

    # Review threshold: reserve manual review for the highest-probability cases,
    # sized to the review capacity rate.
    review_min_p = (
        float(np.quantile(scores, 1.0 - review_capacity_rate))
        if 0 < review_capacity_rate < 1
        else 0.5
    )

    return OperatingPoint(
        step_up_min_p=step_up_min_p,
        review_min_p=review_min_p,
        feasible=feasible,
        achieved_step_up_rate=achieved,
        relaxations=tuple(relaxations),
    )
