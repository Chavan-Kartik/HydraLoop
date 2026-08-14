"""The risk-decision hook: the frozen contract between twin and defender.

Phase 1 ships :class:`AlwaysApprove`. Phase 5 swaps in the cost-sensitive
policy by implementing :class:`RiskDecisionEngine`, without the twin changing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .schema import Action, AuthRequest


@dataclass(frozen=True)
class ReasonCode:
    code: str
    contribution: float


@dataclass(frozen=True)
class BudgetState:
    """Friction and review budget consumed so far on the current day."""

    day_index: int
    step_ups_today: int
    step_up_budget: int
    reviews_today: int
    review_capacity: int

    @property
    def step_up_exhausted(self) -> bool:
        return self.step_ups_today >= self.step_up_budget

    @property
    def review_exhausted(self) -> bool:
        return self.reviews_today >= self.review_capacity


@dataclass(frozen=True)
class DecisionContext:
    as_of: float  # simulation seconds; nothing after this instant may be read
    auth_request: AuthRequest
    features: Mapping[str, float | None]
    budget_state: BudgetState


@dataclass(frozen=True)
class Decision:
    action: Action
    risk_score: float
    rationale: str
    reason_codes: tuple[ReasonCode, ...] = field(default_factory=tuple)
    latency_ms: float = 0.0
    degraded: bool = False


@runtime_checkable
class RiskDecisionEngine(Protocol):
    def decide(self, ctx: DecisionContext) -> Decision: ...


class AlwaysApprove:
    """Phase 1 no-op engine: approves everything at zero risk."""

    def decide(self, ctx: DecisionContext) -> Decision:
        return Decision(
            action=Action.APPROVE,
            risk_score=0.0,
            rationale="no-op engine (Phase 1): all traffic approved",
            reason_codes=(),
            latency_ms=0.0,
        )
