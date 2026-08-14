"""Fidelity harness v0.

Fidelity here means agreement with the *declared* priors and internal
structural validity, not agreement with proprietary ground truth we do not have.
This module reports marginal summaries, a correlation-structure summary, and
lifecycle-validity checks, and renders a small set of plots.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: never try to open a display in CI or on stage
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..paths import REPORTS_DIR  # noqa: E402

_MARGINAL_FEATURES = [
    "amount_minor",
    "velocity_24h",
    "hour_of_day",
    "day_of_week",
    "account_age_days",
]


def _marginals(df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in _MARGINAL_FEATURES:
        if col not in df:
            continue
        s = df[col].dropna().astype(float)
        if s.empty:
            continue
        rows.append(
            {
                "feature": col,
                "mean": float(s.mean()),
                "std": float(s.std()),
                "p05": float(s.quantile(0.05)),
                "p50": float(s.quantile(0.5)),
                "p95": float(s.quantile(0.95)),
            }
        )
    return rows


def _correlation_frobenius(df: pd.DataFrame) -> float:
    num = df[[c for c in _MARGINAL_FEATURES if c in df]].dropna()
    if len(num) < 3:
        return 0.0
    corr = np.corrcoef(num.to_numpy().T)
    off = corr - np.eye(corr.shape[0])
    return float(np.sqrt((off**2).sum()))


def _plots(out_dir: Path, df: pd.DataFrame) -> list[str]:
    made = []
    if "amount_minor" in df and not df["amount_minor"].dropna().empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.hist(np.log1p(df["amount_minor"].astype(float)), bins=40)
        ax.set_title("log(1 + amount_minor)")
        fig.tight_layout()
        p = out_dir / "fidelity_amount_hist.png"
        fig.savefig(p, dpi=110)
        plt.close(fig)
        made.append(p.name)
    if "hour_of_day" in df and not df["hour_of_day"].dropna().empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.hist(df["hour_of_day"].astype(float), bins=24)
        ax.set_title("arrival hour-of-day")
        fig.tight_layout()
        p = out_dir / "fidelity_hour_hist.png"
        fig.savefig(p, dpi=110)
        plt.close(fig)
        made.append(p.name)
    return made


def marginal_divergences(reference: pd.DataFrame, synthetic: pd.DataFrame) -> list[dict]:
    """KS statistic and Wasserstein distance per feature against a reference set."""
    from scipy.stats import ks_2samp, wasserstein_distance

    rows = []
    for col in _MARGINAL_FEATURES:
        if col not in reference or col not in synthetic:
            continue
        r = reference[col].dropna().astype(float).to_numpy()
        s = synthetic[col].dropna().astype(float).to_numpy()
        if len(r) < 5 or len(s) < 5:
            continue
        rows.append(
            {
                "feature": col,
                "ks": float(ks_2samp(r, s).statistic),
                "wasserstein": float(wasserstein_distance(r, s)),
            }
        )
    return rows


def discriminator_auc(reference: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    """Train a classifier to tell reference from synthetic; AUC near 0.5 is good.

    A discriminator that cannot separate the two distributions (AUC ~ 0.5) is
    evidence of fidelity. This is the one fidelity check that benefits from an
    external reference dataset; when none is available without credentials, the
    caller documents that and relies on the declared-prior and sensitivity story
    instead.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    cols = [c for c in _MARGINAL_FEATURES if c in reference and c in synthetic]
    r = reference[cols].dropna().astype(float)
    s = synthetic[cols].dropna().astype(float)
    n = min(len(r), len(s))
    if n < 20:
        return float("nan")
    X = pd.concat([r.iloc[:n], s.iloc[:n]], ignore_index=True).to_numpy()
    y = np.array([0] * n + [1] * n)
    scores = cross_val_score(LogisticRegression(max_iter=500), X, y, cv=3, scoring="roc_auc")
    return float(scores.mean())


def lifecycle_validity(df: pd.DataFrame) -> dict:
    captured_without_approval = int(((df["captured_minor"] > 0) & (~df["approved"])).sum())
    disputed_without_capture = int(((df["disputed"]) & (df["captured_minor"] <= 0)).sum())
    return {
        "captured_without_approval": captured_without_approval,
        "disputed_without_capture": disputed_without_capture,
    }


def write_fidelity_report(out_dir: Path, transactions: list[dict]) -> Path:
    df = pd.DataFrame(transactions)
    marg = _marginals(df)
    frob = _correlation_frobenius(df)
    plots = _plots(out_dir, df)
    validity = lifecycle_validity(df)

    fraud_rate = float(df["is_fraud"].mean()) if "is_fraud" in df else 0.0
    dispute_rate = float(df["disputed"].mean()) if "disputed" in df else 0.0

    lines = ["# Fidelity report (v0)", ""]
    lines.append(f"- transactions: {len(df)}")
    lines.append(f"- fraud rate (ground truth): {fraud_rate:.4f}")
    lines.append(f"- dispute rate: {dispute_rate:.4f}")
    lines.append(f"- correlation-structure Frobenius norm (off-diagonal): {frob:.3f}")
    lines.append("")
    lines.append("## Lifecycle validity (must be zero)")
    for k, v in validity.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Marginal summaries")
    lines.append("")
    lines.append("| feature | mean | std | p05 | p50 | p95 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for m in marg:
        lines.append(
            f"| {m['feature']} | {m['mean']:.2f} | {m['std']:.2f} | "
            f"{m['p05']:.2f} | {m['p50']:.2f} | {m['p95']:.2f} |"
        )
    lines.append("")
    if plots:
        lines.append("## Plots")
        for p in plots:
            lines.append(f"![{p}]({p})")
    report = "\n".join(lines) + "\n"

    (out_dir / "fidelity_report.md").write_text(report, encoding="utf-8")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "fidelity_report.md").write_text(report, encoding="utf-8")
    return out_dir / "fidelity_report.md"
