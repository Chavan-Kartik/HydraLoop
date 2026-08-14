"""Thompson sampling over discrete attack strategies against the live policy.

Each arm is a candidate genome; its reward is the (normalised) fitness it earns
against the current defence. Gaussian Thompson sampling balances exploring new
strategies against exploiting the best one found so far, and converges onto the
arm that survives the policy.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .dsl.genome import Genome


@dataclass
class _Arm:
    pulls: int = 0
    mean: float = 0.0
    m2: float = 0.0  # sum of squared deviations, for a running variance

    def update(self, reward: float) -> None:
        self.pulls += 1
        delta = reward - self.mean
        self.mean += delta / self.pulls
        self.m2 += delta * (reward - self.mean)

    @property
    def var(self) -> float:
        return self.m2 / self.pulls if self.pulls > 1 else 1.0


@dataclass
class ThompsonSampler:
    n_arms: int
    rng: np.random.Generator
    arms: list[_Arm] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.arms:
            self.arms = [_Arm() for _ in range(self.n_arms)]

    def select(self) -> int:
        samples = []
        for arm in self.arms:
            # Sample the posterior mean; unpulled arms get an optimistic wide prior.
            sd = np.sqrt(arm.var / max(1, arm.pulls)) if arm.pulls else 1.0
            samples.append(self.rng.normal(arm.mean, sd + 1e-6))
        return int(np.argmax(samples))

    def update(self, arm: int, reward: float) -> None:
        self.arms[arm].update(reward)

    def best_arm(self) -> int:
        return int(np.argmax([a.mean for a in self.arms]))


def optimise_strategy(
    arms: list[Genome],
    reward_fn: Callable[[Genome], float],
    rounds: int,
    rng: np.random.Generator,
) -> tuple[int, list[int]]:
    """Run Thompson sampling; return the best arm and the pull history."""
    sampler = ThompsonSampler(n_arms=len(arms), rng=rng)
    history: list[int] = []
    for _ in range(rounds):
        a = sampler.select()
        sampler.update(a, reward_fn(arms[a]))
        history.append(a)
    return sampler.best_arm(), history
