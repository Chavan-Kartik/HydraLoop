"""Scenario mixer: run many genomes against one shared population.

Attacks must interfere with each other and with legitimate traffic rather than
run in clean isolation, so all fraud sessions are interleaved on the same clock
as legit traffic by the engine.
"""

from __future__ import annotations

import numpy as np

from ..twin.engine import SessionSpec, TwinEngine
from ..twin.entities import Cardholder
from .dsl.genome import Genome
from .interpreter import interpret_episode
from .ledger import ResourceLedger

_AGE_ANY = "any"


def _balance_bounds(engine: TwinEngine, lo: float, hi: float) -> tuple[float, float]:
    balances = np.array([c.balance_minor for c in engine.pop.cardholders], dtype=float)
    return float(np.quantile(balances, lo)), float(np.quantile(balances, hi))


def _pick_victim(
    engine: TwinEngine, genome: Genome, gen: np.random.Generator
) -> Cardholder:
    vs = genome.genes["victim_selection"]
    lo_val, hi_val = _balance_bounds(engine, vs["balance_percentile_lo"], vs["balance_percentile_hi"])
    candidates = [
        c
        for c in engine.pop.cardholders
        if c.age_band == vs["age_band"] and lo_val <= c.balance_minor <= hi_val
    ]
    if not candidates:
        candidates = engine.pop.cardholders
    return candidates[int(gen.integers(0, len(candidates)))]


def build_attack_specs(
    engine: TwinEngine,
    registry,
    genomes: list[Genome],
    n_fraud_target: int,
    horizon_s: float,
    stream_name: str = "attacks",
) -> tuple[list[SessionSpec], ResourceLedger]:
    ledger = ResourceLedger()
    gen = registry.stream(stream_name)
    specs: list[SessionSpec] = []
    episode = 0
    while len(specs) < n_fraud_target and genomes:
        genome = genomes[episode % len(genomes)]
        holder = _pick_victim(engine, genome, gen)
        # Across the whole horizon, not the first 80% of it. Confining attack starts
        # to an early window leaves the tail of the horizon fraud-free, and since the
        # train/test split is temporal that hands the test set little or no fraud to
        # detect. Episodes that run past the horizon are marked censored by the engine
        # rather than dropped, which is what a real data pull looks like anyway.
        start_ts = float(gen.uniform(0.0, max(1.0, horizon_s)))
        episode_id = f"{genome.attack_id}-{episode:04d}"
        specs.extend(
            interpret_episode(genome, holder, start_ts, gen, ledger, episode_id)
        )
        episode += 1
        if episode > n_fraud_target * 4 + 100:  # safety valve against tiny episodes
            break
    return specs, ledger
