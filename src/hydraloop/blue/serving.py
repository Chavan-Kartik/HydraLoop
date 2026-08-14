"""Latency-instrumented scoring with a degraded-mode fallback.

If the primary scorer breaches the latency budget, serving sticks to a cheaper
fallback scorer (tabular-only once the ensemble exists) and flags the decision
as degraded. This is exactly the resilience question a payments practitioner asks.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ScoreResult:
    prob: float
    latency_ms: float
    degraded: bool


class ScoringService:
    def __init__(
        self,
        primary: Callable[[dict], float],
        fallback: Callable[[dict], float] | None = None,
        latency_budget_ms: float = 150.0,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or primary
        self.latency_budget_ms = latency_budget_ms
        self._degraded = False
        self.latencies_ms: list[float] = []

    def score(self, features: dict) -> ScoreResult:
        scorer = self.fallback if self._degraded else self.primary
        start = time.perf_counter()
        prob = scorer(features)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.latencies_ms.append(elapsed_ms)
        if not self._degraded and elapsed_ms > self.latency_budget_ms:
            # Latch into degraded mode for subsequent calls.
            self._degraded = True
        return ScoreResult(prob=prob, latency_ms=elapsed_ms, degraded=self._degraded)

    def percentiles(self) -> dict[str, float]:
        if not self.latencies_ms:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        import numpy as np

        arr = np.array(self.latencies_ms)
        return {
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
        }
