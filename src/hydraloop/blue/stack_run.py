"""Train the full defence stack and emit the ablation report.

Reports each model alone next to the stacked ensemble, and -- separately -- the
Isolation Forest sentinel's solo recall on the sealed zero-day holdout, which is
the honest answer to "how do you catch what you have never seen".
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config
from ..evaluation.metrics import threshold_at_fpr
from .ensemble import EnsembleDetector
from .features import mature_mask, true_labels
from .models.sentinel import SentinelModel


def _load_or_build_splits(cfg: Config, run_id: str) -> Path:
    from .run import _ensure_splits

    return _ensure_splits(cfg, run_id)


def _sentinel_zeroday_recall(sentinel: SentinelModel, legit_ref: pd.DataFrame) -> float | None:
    """Recall on unseen holdout fraud at a 1% FPR threshold set on known legit.

    The holdout contains only zero-day fraud, so the operating threshold is
    calibrated on in-distribution legitimate traffic, then recall is measured on
    the fraud the sentinel has never seen in any form.
    """
    from ..red.holdout import load_holdout_final

    holdout = load_holdout_final()
    legit = legit_ref[mature_mask(legit_ref) & (~true_labels(legit_ref).astype(bool))]
    fraud = holdout[mature_mask(holdout) & (true_labels(holdout).astype(bool))]
    if legit.empty or fraud.empty:
        return None
    legit_scores = sentinel.predict_proba(legit)
    thr = threshold_at_fpr(np.zeros(len(legit_scores), dtype=int), legit_scores, 0.01)
    fraud_scores = sentinel.predict_proba(fraud)
    return float(np.mean(fraud_scores >= thr))


def train_defense_stack(cfg: Config, run_id: str) -> Path:
    out = _load_or_build_splits(cfg, run_id)
    train = pd.read_parquet(out / "transactions_train.parquet")
    val = pd.read_parquet(out / "transactions_val.parquet")
    test = pd.read_parquet(out / "transactions_test.parquet")

    ensemble = EnsembleDetector(seed=cfg.simulation.seed).fit(train, val)
    table = ensemble.ablation_table(test)
    zeroday_solo = _sentinel_zeroday_recall(ensemble.bases["sentinel"], test)

    report = {
        "run_id": run_id,
        "ablation": table,
        "sentinel_zeroday_solo_recall_at_fpr_1pct": zeroday_solo,
    }
    (out / "ablation_table.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = ["# Defence stack ablation", "", f"- run: {run_id}", ""]
    lines.append("| model | PR-AUC (obs) | recall@1%FPR (obs) | PR-AUC (true) | recall@1%FPR (true) |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in table:
        lines.append(
            f"| {r['model']} | {r['pr_auc_observed']} | {r['recall_at_fpr_observed']} | "
            f"{r['pr_auc_true']} | {r['recall_at_fpr_true']} |"
        )
    lines.append("")
    lines.append(
        f"Isolation Forest sentinel solo recall on the sealed zero-day holdout "
        f"@1% FPR: {zeroday_solo}"
    )
    (out / "defense_stack_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "defense_stack_report.md"
