"""Train the blue-team baseline and emit the metrics report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import Config  # noqa: E402
from ..evaluation.metrics import full_report  # noqa: E402
from ..paths import run_dir  # noqa: E402
from ..red.run import run_static_attacks  # noqa: E402
from .detector import Detector  # noqa: E402
from .features import observed_labels, true_labels  # noqa: E402
from .models import VelocityRuleBaseline  # noqa: E402


def _ensure_splits(cfg: Config, run_id: str) -> Path:
    out = run_dir(run_id)
    if not (out / "transactions_train.parquet").exists():
        run_static_attacks(cfg, run_id)
    return out


def _reliability_plot(out: Path, curve: dict) -> str:
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.plot(curve["confidence"], curve["accuracy"], marker="o")
    ax.set_xlabel("predicted probability")
    ax.set_ylabel("observed frequency")
    ax.set_title("Reliability diagram")
    fig.tight_layout()
    p = out / "reliability_diagram.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    return p.name


def _write_investigations(out: Path, detector, test_df, scores) -> None:
    from .explain import counterfactual, top_reason_codes
    from .features import feature_matrix

    X = feature_matrix(test_df)
    order = scores.argsort()[::-1][:3]
    cases = []
    for i in order:
        row = X[i]
        reasons = top_reason_codes(detector.model, row, k=5)
        cf = counterfactual(detector.model, detector.calibrator, row, "payee_is_new", 0.0)
        cases.append(
            {
                "txn_id": str(test_df.iloc[i]["txn_id"]),
                "risk_score": float(scores[i]),
                "is_fraud": bool(test_df.iloc[i]["is_fraud"]),
                "reason_codes": reasons,
                "counterfactual": cf,
            }
        )
    (out / "investigations.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")


def train_baseline(cfg: Config, run_id: str) -> Path:
    out = _ensure_splits(cfg, run_id)
    train_df = pd.read_parquet(out / "transactions_train.parquet")
    val_df = pd.read_parquet(out / "transactions_val.parquet")
    test_df = pd.read_parquet(out / "transactions_test.parquet")

    detector = Detector(seed=cfg.simulation.seed).fit(train_df, val_df)
    detector.save(out / "detector.pkl")

    scores = detector.score(test_df)
    y_true = true_labels(test_df)
    y_obs = observed_labels(test_df)
    value = test_df["amount_minor"].astype(float).to_numpy()
    review_k = cfg.defender.daily_review_capacity

    rule = VelocityRuleBaseline()
    rule_scores = rule.score(test_df)

    # Detection efficacy is reported against ground truth (the value we want to
    # stop). The ML-vs-rule comparison and calibration are judged against the
    # observed (disputed) label, which is what both models were trained to
    # predict and what a bank actually optimises.
    ml_true = full_report(y_true, scores, value, review_k, prob=scores)
    ml_obs = full_report(y_obs, scores, value, review_k, prob=scores)
    rule_true = full_report(y_true, rule_scores, value, review_k, prob=rule_scores)
    rule_obs = full_report(y_obs, rule_scores, value, review_k, prob=rule_scores)

    ece = ml_obs["ece"]
    plot_name = _reliability_plot(out, ml_obs["reliability"])
    ml_beats_rule = bool(ml_obs["pr_auc"] >= rule_obs["pr_auc"])

    _write_investigations(out, detector, test_df, scores)

    result = {
        "run_id": run_id,
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "test_fraud_true": int(y_true.sum()),
        "test_fraud_observed": int(y_obs.sum()),
        "ece_observed": ece,
        "ece_observed_equal_mass": ml_obs["ece_equal_mass"],
        "ml_beats_rule_observed_pr_auc": ml_beats_rule,
        "ml_vs_true": {k: v for k, v in ml_true.items() if k != "reliability"},
        "ml_vs_observed": {k: v for k, v in ml_obs.items() if k != "reliability"},
        "rule_vs_observed": {k: v for k, v in rule_obs.items() if k != "reliability"},
        "rule_vs_true": {k: v for k, v in rule_true.items() if k != "reliability"},
    }
    (out / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = ["# Metrics report", ""]
    lines.append(f"- run: {run_id}")
    lines.append(
        f"- test transactions: {result['n_test']} "
        f"(true fraud: {result['test_fraud_true']}, observed: {result['test_fraud_observed']})"
    )
    lines.append(
        f"- ECE (observed label): {ece:.4f} equal-width, "
        f"{ml_obs['ece_equal_mass']:.4f} equal-mass"
    )
    lines.append(f"- ML beats velocity rule on observed PR-AUC: {ml_beats_rule}")
    lines.append("")
    lines.append("## Against observed (disputed) label - training target")
    lines.append("")
    lines.append("| metric | ML | velocity rule |")
    lines.append("|---|---:|---:|")
    for key in ["pr_auc", "roc_auc", "recall_at_fpr_1pct", "precision_at_capacity", "ece"]:
        lines.append(f"| {key} | {ml_obs[key]:.4f} | {rule_obs[key]:.4f} |")
    lines.append("")
    lines.append("## Against ground truth - detection efficacy (value stopped)")
    lines.append("")
    lines.append("| metric | ML | velocity rule |")
    lines.append("|---|---:|---:|")
    for key in [
        "pr_auc",
        "recall_at_fpr_0.5pct",
        "recall_at_fpr_1pct",
        "value_detection_rate_at_fpr_1pct",
    ]:
        lines.append(f"| {key} | {ml_true[key]:.4f} | {rule_true[key]:.4f} |")
    lines.append("")
    lines.append(f"![reliability]({plot_name})")
    (out / "metrics_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "metrics_report.md"
