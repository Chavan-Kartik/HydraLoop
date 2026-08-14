"""Assemble a mixed legit-plus-adversarial dataset and split it for training.

The main dataset is split temporally (train on early generations, test on late),
never shuffled. The four zero-day scenarios are written to a physically separate
holdout directory and excluded from every training split.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..catalog import load_catalog
from ..config import Config
from ..paths import HOLDOUT_DIR, run_dir
from ..twin.population import SECONDS_PER_DAY
from ..twin.run import build_engine, legit_session_specs
from ..twin.writer import write_dataset
from .dsl.genome import genome_from_template
from .dsl.render import render_brief
from .holdout import HOLDOUT_ATTACK_IDS, is_holdout
from .mixer import build_attack_specs


def _training_and_holdout_genomes():
    scenarios = [s for s in load_catalog() if s.evolvable]
    training, holdout = [], []
    for s in scenarios:
        g = genome_from_template(s.family, s.attack_id, s.genome_template)
        (holdout if is_holdout(s.attack_id) else training).append(g)
    return training, holdout


def _temporal_split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = df.sort_values("ts").reset_index(drop=True)
    n = len(df)
    a, b = int(n * 0.70), int(n * 0.85)
    return {"train": df.iloc[:a], "val": df.iloc[a:b], "test": df.iloc[b:]}


def run_static_attacks(cfg: Config, run_id: str) -> Path:
    engine, registry = build_engine(cfg)
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    legit_target = cfg.simulation.legitimate_transactions_per_generation
    legit = legit_session_specs(cfg, engine, registry, legit_target)

    fraud_rate = cfg.simulation.fraud_rate_target
    fraud_target = max(30, int(fraud_rate / max(1e-6, 1 - fraud_rate) * legit_target))

    training_genomes, holdout_genomes = _training_and_holdout_genomes()
    train_fraud, train_ledger = build_attack_specs(
        engine, registry, training_genomes, fraud_target, horizon_s, "attacks:train"
    )
    holdout_fraud, holdout_ledger = build_attack_specs(
        engine, registry, holdout_genomes, max(20, fraud_target // 3), horizon_s, "attacks:holdout"
    )

    result = engine.simulate(legit + train_fraud + holdout_fraud)
    tx = pd.DataFrame(result.transactions)

    holdout_mask = tx["attack_id"].apply(is_holdout)
    main_tx = tx[~holdout_mask].reset_index(drop=True)
    holdout_tx = tx[holdout_mask].reset_index(drop=True)

    out = run_dir(run_id)
    write_dataset(out, result.events, main_tx.to_dict("records"), tag="mixed")
    splits = _temporal_split(main_tx)
    for name, part in splits.items():
        part.to_parquet(out / f"transactions_{name}.parquet", index=False)

    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
    holdout_tx.to_parquet(HOLDOUT_DIR / "transactions_holdout.parquet", index=False)
    (HOLDOUT_DIR / "README.txt").write_text(
        "Zero-day holdout. Sealed: only the holdout guard can unseal it, and only "
        "for final evaluation. Training never reads this directory.\n"
        f"Attack ids: {sorted(HOLDOUT_ATTACK_IDS)}\n",
        encoding="utf-8",
    )

    genomes_manifest = [
        {
            "attack_id": g.attack_id,
            "genome_id": g.genome_id,
            "family": g.family,
            "brief": render_brief(g),
            "role": "training",
        }
        for g in training_genomes
    ] + [
        {
            "attack_id": g.attack_id,
            "genome_id": g.genome_id,
            "family": g.family,
            "brief": render_brief(g),
            "role": "holdout",
        }
        for g in holdout_genomes
    ]
    (out / "genomes.json").write_text(json.dumps(genomes_manifest, indent=2), encoding="utf-8")

    summary = {
        "legit": int((~tx["is_fraud"]).sum()),
        "fraud_train_region": int(main_tx["is_fraud"].sum()),
        "holdout_fraud": int(holdout_tx["is_fraud"].sum()) if len(holdout_tx) else 0,
        "fraud_rate_main": float(main_tx["is_fraud"].mean()),
        "resource_totals_train": train_ledger.totals(),
        "resource_totals_holdout": holdout_ledger.totals(),
        "ledger_balanced": train_ledger.balances() and holdout_ledger.balances(),
        "splits": {k: len(v) for k, v in splits.items()},
    }
    (out / "attack_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out / "transactions_mixed.parquet"
