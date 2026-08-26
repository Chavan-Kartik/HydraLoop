"""The co-evolution loop.

Each generation: the red team mutates the attacks that escaped last time, the
twin runs them against the live policy, the blue team mines the new escapes,
retrains on immune memory, and the regression gauntlet decides whether the
candidate is promoted or rolled back. Every generation is sealed into the
hash-chained ledger.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..blue.policy import build_policy_engine
from ..config import Config
from ..paths import run_dir
from ..red.dsl.genome import Genome, genome_from_template
from ..red.dsl.mutate import mutate
from ..red.llm import LLMClient
from ..red.mixer import build_attack_specs
from ..red.strategist import Strategist, audit_report
from ..twin.decision import AlwaysApprove
from ..twin.population import SECONDS_PER_DAY
from ..twin.run import build_engine, legit_session_specs
from .escape_analysis import cluster_escapes, escaped_frame
from .gauntlet import ModelRegistry, run_gauntlet
from .immune_memory import ImmuneMemory
from .ledger import GenerationLedger


def _seed_generation(cfg: Config, generation: int) -> Config:
    sim = dataclasses.replace(cfg.simulation, seed=cfg.simulation.seed + generation)
    return dataclasses.replace(cfg, simulation=sim)


def _base_genomes(cfg: Config) -> list[Genome]:
    from ..catalog import load_catalog
    from ..red.holdout import is_holdout

    genomes = []
    for s in load_catalog():
        if s.evolvable and not is_holdout(s.attack_id):
            genomes.append(genome_from_template(s.family, s.attack_id, s.genome_template))
    return genomes


def _evolve(parents: list[Genome], escaped_ids: set[str], registry, rate: float) -> list[Genome]:
    """Mutate the genomes whose attacks escaped; keep the rest as-is."""
    gen = registry.stream("red:evolve")
    children: list[Genome] = []
    for g in parents:
        children.append(g)
        if g.genome_id in escaped_ids or not escaped_ids:
            children.append(mutate(g, gen, rate))
    return children


# One call per escaping genome would make a run's latency scale with the catalog,
# and the population already doubles every generation. A small fixed number is
# enough for the model to steer the search without dominating the runtime.
STRATEGIST_PROPOSALS_PER_GENERATION = 2


def _strategist_children(
    strategist: Strategist, parents: list[Genome], escaped_ids: set[str], context: dict
) -> list[Genome]:
    """Model-proposed children for the genomes that got through last generation.

    Escapees are targeted first, since those are the attacks worth strengthening.
    Each proposal passes the strategist's three tiers, so an invalid one costs a
    deterministic mutation rather than the run.
    """
    targets = [g for g in parents if g.genome_id in escaped_ids] or parents
    return [
        strategist.propose(p, context)
        for p in targets[:STRATEGIST_PROPOSALS_PER_GENERATION]
    ]


def _generation_audit(strategist: Strategist | None, mark: int) -> dict:
    """Strategist counts for this generation only, for the ledger entry."""
    if strategist is None:
        return {"enabled": False, "proposals": 0, "accepted": 0, "refused": 0}
    fresh = strategist.audit_log[mark:]
    return {
        "enabled": True,
        "proposals": len(fresh),
        "accepted": sum(1 for e in fresh if e.accepted),
        "refused": sum(1 for e in fresh if not e.accepted),
    }


def _run_generation_sim(cfg_g: Config, genomes: list[Genome], decision_engine, defender_cfg):
    engine, registry = build_engine(cfg_g)
    horizon_s = cfg_g.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(
        cfg_g, engine, registry, cfg_g.simulation.legitimate_transactions_per_generation
    )
    fraud_rate = cfg_g.simulation.fraud_rate_target
    fraud_target = max(
        40, int(fraud_rate / max(1e-6, 1 - fraud_rate) * len(legit))
    )
    fraud, _ = build_attack_specs(engine, registry, genomes, fraud_target, horizon_s)
    engine.decision = decision_engine
    result = engine.simulate(legit + fraud, defender_cfg)
    return pd.DataFrame(result.transactions), registry


def _hard_negative_frame(train_df: pd.DataFrame, escape_txn_ids: set[str], boost: int) -> pd.DataFrame:
    """Upsample the specific escapes so the retrain focuses on what it missed."""
    if not escape_txn_ids or boost <= 1:
        return train_df
    hard = train_df[train_df["txn_id"].isin(escape_txn_ids)]
    if hard.empty:
        return train_df
    return pd.concat([train_df] + [hard] * (boost - 1), ignore_index=True)


def _split_train_val(df: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("ts").reset_index(drop=True)
    cut = int(len(df) * 0.8)
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def run_loop(
    cfg: Config,
    run_id: str,
    generations: int = 5,
    rollback_demo_generation: int = 2,
    llm: LLMClient | None = None,
) -> Path:
    """Run the co-evolution loop, optionally with a model proposing genomes.

    With ``llm`` unset the red team's variation is exactly the deterministic
    mutation it has always been, so an offline run is unchanged. With a client,
    a schema-constrained strategist also proposes genomes each generation and
    its accepts and refusals are recorded per generation in the ledger.
    """
    out = run_dir(run_id)
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = out / "generation_ledger.jsonl"
    ledger_path.unlink(missing_ok=True)  # a run starts a fresh chain
    ledger = GenerationLedger(ledger_path)
    memory = ImmuneMemory(seed=cfg.simulation.seed)
    registry_rng = build_engine(cfg)[1]
    registry = ModelRegistry(out / "detector.pkl")

    genomes = _base_genomes(cfg)
    # Built only when a model is configured, so the offline path keeps its exact
    # previous behaviour rather than gaining a second source of variation.
    strategist = (
        Strategist(rng=np.random.default_rng(cfg.simulation.seed), llm=llm)
        if llm is not None
        else None
    )
    proposals: list[Genome] = []
    escaped_ids: set[str] = set()
    prev_escape_rate: float | None = None
    escapes_closed_total = 0
    rollbacks = 0
    defender_cfg = {
        "step_up_budget": max(1, int(cfg.defender.step_up_budget_rate
                                     * cfg.simulation.legitimate_transactions_per_generation)),
        "review_capacity": cfg.defender.daily_review_capacity,
    }

    for g in range(1, generations + 1):
        cfg_g = _seed_generation(cfg, g)
        audit_mark = len(strategist.audit_log) if strategist is not None else 0

        if g > 1:
            genomes = _evolve(genomes, escaped_ids, registry_rng, cfg.red_team.mutation_rate)
            if strategist is not None:
                children = _strategist_children(
                    strategist,
                    genomes,
                    escaped_ids,
                    {
                        "generation": g,
                        "previous_escape_rate": prev_escape_rate,
                        "escaping_genomes": len(escaped_ids),
                    },
                )
                proposals.extend(children)
                genomes = genomes + children

        # 1. Simulate against the live policy (AlwaysApprove before a model exists).
        if registry.incumbent is None:
            decision_engine = AlwaysApprove()
        else:
            val_ref = memory.all_data()
            decision_engine = build_policy_engine(cfg_g, registry.incumbent, val_ref)
        gen_df, _ = _run_generation_sim(cfg_g, genomes, decision_engine, defender_cfg)

        # 2. Measure escapes (fraud the policy approved).
        esc = escaped_frame(gen_df)
        n_fraud = int(gen_df["is_fraud"].sum())
        escape_rate = float(len(esc) / n_fraud) if n_fraud else 0.0
        clusters = cluster_escapes(gen_df, seed=cfg.simulation.seed)
        escaped_ids = {str(x) for x in esc["genome_id"].dropna().tolist()}
        escape_txn_ids = {str(x) for x in esc["txn_id"].tolist()}

        if prev_escape_rate is not None and escape_rate < prev_escape_rate - 1e-9:
            escapes_closed_total += 1

        # 3. Add to immune memory and assemble the retraining frame.
        memory.add_generation(gen_df, g)
        full = memory.training_frame()
        train_df, val_df = _split_train_val(full, cfg.simulation.seed)

        gate_events: list[dict] = []
        promoted = False

        # 3a. Deliberately propose a regressed candidate once, to exercise rollback.
        if g == rollback_demo_generation and registry.incumbent is not None:
            fraud_rows = train_df[train_df["is_fraud"]]
            rng = np.random.default_rng(cfg.simulation.seed)
            keep = fraud_rows.sample(frac=0.1, random_state=int(rng.integers(0, 1_000_000))) \
                if len(fraud_rows) else fraud_rows
            starved = pd.concat([train_df[~train_df["is_fraud"]], keep], ignore_index=True)
            bad = Detector(seed=cfg.simulation.seed).fit(starved, val_df)
            res_bad = run_gauntlet(
                registry.incumbent, bad, val_df[~val_df["is_fraud"]],
                memory.replay_archive(), cfg.defender.step_up_budget_rate,
            )
            gate_events.append({"candidate": "fraud-starved-retrain", "result": res_bad.reason,
                                "promoted": res_bad.promote})
            if not res_bad.promote:
                registry.rollback()
                rollbacks += 1

        # 3b. The honest candidate: full immune memory + hard-negative mining.
        mined = _hard_negative_frame(train_df, escape_txn_ids, boost=3)
        candidate = Detector(seed=cfg.simulation.seed).fit(mined, val_df)
        res = run_gauntlet(
            registry.incumbent, candidate, val_df[~val_df["is_fraud"]],
            memory.replay_archive(), cfg.defender.step_up_budget_rate,
        )
        gate_events.append({"candidate": "immune-memory-retrain", "result": res.reason,
                            "promoted": res.promote})
        if res.promote:
            registry.promote(candidate)
            promoted = True
        else:
            registry.rollback()
            rollbacks += 1

        payload = {
            "generation": g,
            "seed": cfg_g.simulation.seed,
            "config_hash": cfg.config_hash,
            "n_transactions": int(len(gen_df)),
            "n_fraud": n_fraud,
            "escapes": int(len(esc)),
            "escape_rate": round(escape_rate, 4),
            "escape_clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "size": c.size,
                    "dominant_attack_id": c.dominant_attack_id,
                    "dominant_genome": c.dominant_family,
                }
                for c in clusters
            ],
            "n_genomes": len(genomes),
            "candidate_archive_recall": round(res.candidate_recall, 4),
            "incumbent_archive_recall": round(res.incumbent_recall, 4),
            "gate_events": gate_events,
            "promoted": promoted,
            "strategist": _generation_audit(strategist, audit_mark),
        }
        ledger.append(payload)
        prev_escape_rate = escape_rate

    # Written only for a model-driven run, so the Strategist screen shows this
    # run's own proposals instead of falling back to the committed example.
    report = audit_report(strategist, proposals, llm) if strategist is not None else None
    if report is not None:
        (out / "strategist_audit.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

    headline = ("provider", "model", "available", "proposals", "accepted", "refused", "llm_authored")
    summary = {
        "run_id": run_id,
        "generations": generations,
        "escapes_closed_total": escapes_closed_total,
        "rollbacks": rollbacks,
        "ledger_entries": len(ledger.entries),
        "ledger_head": ledger.head_hash,
        "strategist": (
            {k: report[k] for k in headline}
            if report is not None
            else {
                "provider": "none",
                "model": None,
                "available": False,
                "proposals": 0,
                "accepted": 0,
                "refused": 0,
                "llm_authored": 0,
            }
        ),
    }
    (out / "loop_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Verify the on-disk ledger reconstructs and validates.
    GenerationLedger.load(ledger_path)
    return out / "loop_summary.json"


def run_coevolution(cfg: Config, run_id: str, generations: int | None = None) -> Path:
    """CLI entry point: run the loop for the configured number of generations."""
    gens = generations or cfg.simulation.generations or 5
    run_loop(cfg, run_id, generations=gens)
    return run_dir(run_id) / "generation_ledger.jsonl"
