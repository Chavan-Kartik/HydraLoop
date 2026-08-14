"""Wire the twin together and expose the entry point the CLI calls."""

from __future__ import annotations

from pathlib import Path

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
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    arrivals = population_arrivals(registry, engine.pop.cardholders, horizon_s)
    arrivals = arrivals[:target]
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
