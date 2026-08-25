"""Wire the twin together and expose the entry point the CLI calls."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import Config
from ..paths import run_dir
from .arrivals import population_arrivals
from .engine import SessionSpec, TwinEngine
from .labels import LabelModel
from .population import SECONDS_PER_DAY, build_population
from .rng import RngRegistry
from .writer import write_dataset


def build_engine(cfg: Config) -> tuple[TwinEngine, RngRegistry]:
    sim = cfg.simulation
    registry = RngRegistry(sim.seed)
    horizon_s = sim.horizon_days * SECONDS_PER_DAY
    # Size the population so arrivals comfortably exceed the event target.
    target = sim.legitimate_transactions_per_generation
    n_cardholders = max(50, target // 4)
    n_merchants = max(20, n_cardholders // 20)
    pop = build_population(registry, n_cardholders, n_merchants)
    labels = LabelModel(
        delay_hours_mean=sim.label_delay_hours_mean,
        delay_hours_std=sim.label_delay_hours_std,
        friendly_fraud_rate=sim.friendly_fraud_rate,
        under_report_rate=sim.under_report_rate,
        dispute_window_days=sim.dispute_window_days,
    )
    engine = TwinEngine(pop, registry, labels, horizon_s)
    return engine, registry


def legit_session_specs(cfg: Config, engine: TwinEngine, registry: RngRegistry, target: int) -> list[SessionSpec]:
    """Legitimate sessions covering the whole horizon, thinned down to ``target``.

    The population deliberately over-generates so arrivals exceed the target, which
    means the surplus has to be dropped. It must be dropped *uniformly*, not by
    slicing the front of the list: ``population_arrivals`` returns time-sorted
    arrivals, so keeping the first ``target`` of them confines legitimate traffic to
    the opening days of the horizon while attack sessions stay spread across all of
    it. A temporal train/test split then lands inside that dense opening window and
    files almost every fraudulent row into test -- training sees a handful of
    positives and no supervised model can learn. Uniform thinning of a Poisson
    process is itself a Poisson process, so the diurnal and weekly shape survives.
    """
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    arrivals = population_arrivals(registry, engine.pop.cardholders, horizon_s)
    if target < len(arrivals):
        gen = registry.stream("arrivals:thin")
        keep = np.sort(gen.choice(len(arrivals), size=target, replace=False))
        arrivals = [arrivals[i] for i in keep]
    return [SessionSpec(ts=ts, cardholder_id=cid) for ts, cid in arrivals]


def generate_legit_traffic(cfg: Config, run_id: str, event_target: int | None = None) -> Path:
    target = event_target or cfg.simulation.legitimate_transactions_per_generation
    engine, registry = build_engine(cfg)
    specs = legit_session_specs(cfg, engine, registry, target)
    result = engine.simulate(specs)
    out = run_dir(run_id)
    paths = write_dataset(out, result.events, result.transactions, tag="legit")

    from ..evaluation.fidelity import write_fidelity_report

    write_fidelity_report(out, result.transactions)
    return paths["transactions"]
