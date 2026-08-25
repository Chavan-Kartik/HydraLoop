"""Produce the one evaluation artifact the submission quotes.

Run this and every detection number in the write-up can be regenerated from a
single deterministic command. The defaults are chosen for statistical power
rather than speed: the temporal test split is the tail of the horizon, and
multi-session attack episodes that start near the end are right-censored, so a
small simulation leaves the test window with single-digit fraud rows and no
number computed on it means anything.

Usage:
    python scripts/canonical_eval.py
    python scripts/canonical_eval.py --legit 20000 --horizon 60 --run-id quick
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hydraloop.blue.run import train_baseline  # noqa: E402
from hydraloop.config import Config, load_config  # noqa: E402
from hydraloop.evaluation.metrics import precision_at_prevalence  # noqa: E402
from hydraloop.paths import run_dir  # noqa: E402

# The base rate a card portfolio actually sees. The simulator runs a far richer
# fraud mix to get enough positives to measure; precision is restated here.
REALISTIC_PREVALENCE = 0.005


def build_config(legit: int, horizon: int, fraud_rate: float, seed: int) -> Config:
    base = load_config()
    sim = dataclasses.replace(
        base.simulation,
        seed=seed,
        legitimate_transactions_per_generation=legit,
        fraud_rate_target=fraud_rate,
        horizon_days=horizon,
    )
    return Config(raw=base.raw, simulation=sim, defender=base.defender, red_team=base.red_team)


def summarise(metrics: dict) -> dict:
    """Pull the comparison down to the numbers that are defensible."""
    out: dict = {
        "n_test": metrics["n_test"],
        "test_fraud_true": metrics["test_fraud_true"],
        "ece_observed_equal_mass": metrics["ece_observed_equal_mass"],
        "realistic_prevalence": REALISTIC_PREVALENCE,
    }
    for side in ("ml_vs_true", "rule_vs_true", "ml_vs_observed", "rule_vs_observed"):
        d = metrics[side]
        c = d["confusion_at_fpr_1pct"]
        out[side] = {
            "pr_auc": round(d["pr_auc"], 4),
            "roc_auc": round(d["roc_auc"], 4),
            "recall_at_fpr_1pct": round(d["recall_at_fpr_1pct"], 4),
            "value_detection_rate_at_fpr_1pct": round(d["value_detection_rate_at_fpr_1pct"], 4),
            "confusion": {k: c[k] for k in ("tp", "fp", "fn", "tn")},
            "precision_at_test_prevalence": round(c["precision"], 4),
            "recall": round(c["recall"], 4),
            "f1_at_test_prevalence": round(c["f1"], 4),
            "realised_fpr": round(c["fpr"], 5),
            "test_prevalence": round(c["prevalence"], 5),
            "precision_at_realistic_prevalence": round(
                precision_at_prevalence(c["recall"], c["fpr"], REALISTIC_PREVALENCE), 4
            ),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legit", type=int, default=60000)
    ap.add_argument("--horizon", type=int, default=120)
    ap.add_argument("--fraud-rate", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--run-id", default="run_canonical")
    args = ap.parse_args()

    cfg = build_config(args.legit, args.horizon, args.fraud_rate, args.seed)
    print(
        f"simulating: legit={args.legit} horizon={args.horizon}d "
        f"fraud_rate={args.fraud_rate} seed={args.seed}"
    )
    train_baseline(cfg, args.run_id)

    out = run_dir(args.run_id)
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    summary = summarise(metrics)
    summary["config"] = {
        "legit": args.legit,
        "horizon_days": args.horizon,
        "fraud_rate_target": args.fraud_rate,
        "seed": args.seed,
    }
    path = out / "canonical_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\ntest rows {summary['n_test']}, true fraud {summary['test_fraud_true']}")
    hdr = f"{'':<26}{'PR-AUC':>9}{'ROC':>8}{'R@1%FPR':>10}{'VDR':>8}{'F1':>7}{'prec@0.5%':>11}"
    print("\n" + hdr)
    for side in ("ml_vs_true", "rule_vs_true"):
        d = summary[side]
        print(
            f"{side:<26}{d['pr_auc']:>9.4f}{d['roc_auc']:>8.4f}"
            f"{d['recall_at_fpr_1pct']:>10.4f}{d['value_detection_rate_at_fpr_1pct']:>8.4f}"
            f"{d['f1_at_test_prevalence']:>7.3f}{d['precision_at_realistic_prevalence']:>11.4f}"
        )
    ml, rule = summary["ml_vs_true"], summary["rule_vs_true"]
    print(f"\nwrote {path}")
    if summary["test_fraud_true"] < 100:
        print(
            f"WARNING: only {summary['test_fraud_true']} fraud rows in test -- "
            "too few to quote. Raise --legit or --horizon."
        )
    print(
        "ML beats velocity rule at 1% FPR: "
        f"{ml['recall_at_fpr_1pct'] > rule['recall_at_fpr_1pct']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
