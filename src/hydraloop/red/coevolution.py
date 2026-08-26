"""Gate G4 driver: quality-diversity red search against a strengthening policy.

Each generation the blue team retrains on the attacks discovered so far, so the
live policy hardens; the red team then runs MAP-Elites (seeded by the strategist
and refined by a Thompson-sampling bandit) against that policy. Over generations
the best attacker ROI collapses while behavioural coverage climbs and friction
stays inside budget -- the co-evolutionary signature.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..blue.policy import build_policy_engine
from ..config import Config
from ..paths import run_dir
from ..twin.run import build_engine, legit_session_specs
from .bandit import optimise_strategy
from .dsl.genome import Genome, genome_from_template
from .economics import FitnessWeights, evaluate_genome, fitness
from .llm import LLMClient
from .mapelites import MapElitesArchive, run_map_elites
from .strategist import Strategist, audit_report


def _base_seeds() -> list[Genome]:
    from ..catalog import load_catalog
    from .holdout import is_holdout

    seeds = []
    for s in load_catalog():
        if s.evolvable and not is_holdout(s.attack_id):
            seeds.append(genome_from_template(s.family, s.attack_id, s.genome_template))
    return seeds


def _initial_legit(cfg: Config) -> pd.DataFrame:
    engine, registry = build_engine(cfg)
    legit = legit_session_specs(cfg, engine, registry, cfg.simulation.legitimate_transactions_per_generation)
    return pd.DataFrame(engine.simulate(legit).transactions)


def _build_policy(cfg: Config, legit_df: pd.DataFrame, fraud_accum: list[pd.DataFrame]):
    if not fraud_accum:
        return None
    train = pd.concat([legit_df, *fraud_accum], ignore_index=True).sort_values("ts")
    cut = int(len(train) * 0.8)
    tr, val = train.iloc[:cut], train.iloc[cut:]
    detector = Detector(seed=cfg.simulation.seed).fit(tr, val)
    return build_policy_engine(cfg, detector, val)


def _run_generation(cfg, policy, seeds, strategist, rng, weights,
                    qd_iterations, n_episodes, bandit_rounds, archive, generation):
    collected: list[pd.DataFrame] = []

    def evaluate(genome: Genome) -> float:
        outcome, tx = evaluate_genome(cfg, genome, policy, n_episodes)
        if not tx.empty:
            collected.append(tx[tx["is_fraud"]])
        return fitness(outcome, weights)

    # The strategist proposes new genomes each generation; when an LLM is wired in
    # these are model-authored (schema-validated), otherwise deterministic.
    proposals = [
        strategist.propose(rng.choice(seeds), {"generation": generation})
        for _ in range(3)
    ]
    gen_seeds = seeds + proposals
    archive = run_map_elites(gen_seeds, evaluate, qd_iterations, rng, archive=archive)

    elites = sorted(archive.cells.values(), key=lambda e: e.fitness, reverse=True)[:8]
    if len(elites) >= 2:
        optimise_strategy(
            [e.genome for e in elites],
            lambda gnome: fitness(evaluate_genome(cfg, gnome, policy, n_episodes)[0], weights),
            bandit_rounds,
            rng,
        )
    return archive, elites, collected, proposals


def run_coevolution_economics(
    cfg: Config,
    run_id: str,
    generations: int = 15,
    qd_iterations: int = 24,
    n_episodes: int = 30,
    bandit_rounds: int = 40,
    llm: LLMClient | None = None,
) -> Path:
    """Run the quality-diversity search, optionally with a model in the strategist.

    Takes an already-built client rather than provider strings so there is one
    way to construct one. The previous string form silently dropped the API key,
    which meant every hosted provider resolved to no client while the audit file
    still named it.
    """
    out = run_dir(run_id)
    rng = np.random.default_rng(cfg.simulation.seed)
    weights = FitnessWeights()

    strategist = Strategist(rng=rng, llm=llm)
    all_proposals: list[Genome] = []

    legit_df = _initial_legit(cfg)
    fraud_accum: list[pd.DataFrame] = []
    base_seeds = _base_seeds()
    seeds = list(base_seeds)
    curve = []
    archive = MapElitesArchive()  # persists across generations so coverage climbs

    for g in range(1, generations + 1):
        # Blue hardens: retrain on legit plus every attack discovered so far.
        policy = _build_policy(cfg, legit_df, fraud_accum)
        archive, elites, collected, proposals = _run_generation(
            cfg, policy, base_seeds + seeds, strategist, rng, weights,
            qd_iterations, n_episodes, bandit_rounds, archive, g,
        )
        all_proposals.extend(proposals)

        best = archive.best()
        best_outcome, _ = evaluate_genome(cfg, best.genome, policy, n_episodes)
        friction_rate = best_outcome.friction_events / max(1, best_outcome.n_attempts)
        curve.append(
            {
                "generation": g,
                "best_roi": round(best_outcome.roi, 4),
                "best_value_settled": round(best_outcome.value_settled, 2),
                "coverage": round(archive.coverage, 4),
                "novelty": round(archive.mean_novelty(), 4),
                "best_friction_rate": round(friction_rate, 4),
                "elite_count": len(archive.cells),
            }
        )

        if collected:
            fraud_accum.append(pd.concat(collected, ignore_index=True))
        seeds = [e.genome for e in elites] or seeds

    strategist_report = audit_report(strategist, all_proposals, llm)
    (out / "strategist_audit.json").write_text(
        json.dumps(strategist_report, indent=2), encoding="utf-8"
    )

    roi0 = curve[0]["best_roi"]
    roin = curve[-1]["best_roi"]
    summary = {
        "run_id": run_id,
        "generations": generations,
        "roi_start": roi0,
        "roi_end": roin,
        "roi_collapsed": bool(roin < roi0),
        "coverage_start": curve[0]["coverage"],
        "coverage_end": curve[-1]["coverage"],
        "coverage_climbed": bool(curve[-1]["coverage"] >= curve[0]["coverage"]),
        "max_friction_rate": max(c["best_friction_rate"] for c in curve),
        "audit_entries": len(strategist.audit_log),
        "refusals": len(strategist.refusals()),
        "strategist": {
            "provider": strategist_report["provider"],
            "model": strategist_report["model"],
            "available": strategist_report["available"],
            "accepted": strategist_report["accepted"],
            "refused": strategist_report["refused"],
            "llm_authored": strategist_report["llm_authored"],
        },
        "curve": curve,
    }
    (out / "coevolution_economics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out / "coevolution_economics.json"
