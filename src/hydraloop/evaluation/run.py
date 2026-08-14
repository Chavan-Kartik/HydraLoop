"""The Phase 10 evaluation driver.

Produces the LOFO transfer matrix, the supervised-vs-sentinel zero-day split, an
adversarial-holdout escape rate against a frozen model, a drift check with a
PSI/KL hook, a fidelity summary, and a sensitivity tornado over the registered
assumptions. Writes a single evaluation report plus the tornado plot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..blue.detector import Detector
from ..blue.ensemble import EnsembleDetector
from ..config import Config
from ..paths import run_dir
from .drift import DriftMonitor
from .fidelity import discriminator_auc, marginal_divergences
from .lofo import build_family_frames, transfer_matrix
from .sensitivity import Assumption, plot_tornado, sweep
from .zeroday import adversarial_escape_rate, zeroday_split


def _drift_probe(legit_df: pd.DataFrame) -> dict:
    amt = legit_df["amount_minor"].astype(float).to_numpy()
    half = len(amt) // 2
    monitor = DriftMonitor(reference=amt[:half])
    stable = monitor.check(amt[half:])
    # Inject a deliberate +40% upward shift on legit amounts to prove the hook fires.
    drifted = monitor.check(amt[half:] * 1.4 + amt.mean())
    return {"stable": stable, "injected_shift": drifted}


def _sensitivity(cfg: Config) -> tuple[list, dict]:
    from ..blue.costs import CostModel, expected_losses
    from ..twin.schema import Action

    # A cheap, deterministic target metric: the expected loss of the policy's
    # preferred action at a representative risk and value, as cost assumptions move.
    def metric(params: dict[str, float]) -> float:
        cost = CostModel(
            loss_given_fraud=params["loss_given_fraud"],
            false_positive_value_frac=params["false_positive_value_frac"],
            review_cost_minor=params["review_cost_minor"],
        )
        losses = expected_losses(p=0.2, value_minor=50000, cost=cost)
        return float(min(losses.values()))

    base = {"loss_given_fraud": 1.0, "false_positive_value_frac": 0.15, "review_cost_minor": 300.0}
    assumptions = [Assumption.pm50(k, v) for k, v in base.items()]
    rows = sweep(metric, assumptions, base)
    _ = Action  # referenced to keep the action space explicit in context
    return rows, base


def run_evaluation(cfg: Config, run_id: str) -> Path:
    out = run_dir(run_id)

    legit_df, family_frauds = build_family_frames(cfg)
    lofo = transfer_matrix(legit_df, family_frauds, seed=cfg.simulation.seed)

    # Train the supervised stack and a frozen detector on a within-distribution mix.
    all_fraud = pd.concat(family_frauds.values(), ignore_index=True)
    mixed = pd.concat([legit_df, all_fraud], ignore_index=True).sort_values("ts").reset_index(drop=True)
    cut = int(len(mixed) * 0.8)
    train, val = mixed.iloc[:cut], mixed.iloc[cut:]
    ensemble = EnsembleDetector(seed=cfg.simulation.seed).fit(train, val)
    frozen = Detector(seed=cfg.simulation.seed).fit(train, val)

    from ..red.holdout import load_holdout_final

    holdout = load_holdout_final()
    # The FPR threshold must be set on *mature* legit; the late val slice is
    # largely censored, so the full legit frame is the reference here.
    zd = zeroday_split(
        supervised_score=ensemble.score,
        sentinel_score=ensemble.bases["sentinel"].predict_proba,
        legit_ref=legit_df,
        holdout=holdout,
    )
    adv = adversarial_escape_rate(frozen.score, legit_df, holdout)

    drift = _drift_probe(legit_df)

    # Fidelity: with no external reference, compare two independent synthetic draws
    # (documented credential-free fallback), so the discriminator should be ~0.5.
    shuffled = legit_df.sample(frac=1.0, random_state=cfg.simulation.seed).reset_index(drop=True)
    mid = len(shuffled) // 2
    ref_split, synth_split = shuffled.iloc[:mid], shuffled.iloc[mid:]
    fidelity = {
        "discriminator_auc": discriminator_auc(ref_split, synth_split),
        "reference": "credential-free fallback: synthetic split (no external dataset bundled)",
        "marginals": marginal_divergences(ref_split, synth_split),
    }

    tornado_rows, base = _sensitivity(cfg)
    tornado_path = out / "sensitivity_tornado.png"
    plot_tornado(tornado_rows, tornado_path, metric_name="expected loss")

    report = {
        "run_id": run_id,
        "lofo": lofo,
        "zeroday": zd,
        "adversarial_holdout_escape_rate": adv,
        "drift": drift,
        "fidelity": fidelity,
        "sensitivity": {
            "base": base,
            "tornado": [
                {"name": r.name, "low": r.low_metric, "high": r.high_metric, "swing": r.swing}
                for r in tornado_rows
            ],
        },
    }
    (out / "evaluation.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    lines = ["# Evaluation report", "", f"- run: {run_id}", ""]
    lines.append("## LOFO transfer (train row -> test col), recall@1%FPR")
    lines.append("")
    header = "| train\\test | " + " | ".join(lofo["families"]) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(lofo["families"]) + 1))
    for fam, row in zip(lofo["families"], lofo["matrix"], strict=True):
        lines.append(f"| {fam} | " + " | ".join("-" if v is None else f"{v:.2f}" for v in row) + " |")
    lines.append("")
    lines.append(f"- weak transfer cells (recall < 0.30): {len(lofo['weak_cells'])}")
    lines.append(f"- zero-day supervised recall: {zd['supervised_recall']}")
    lines.append(f"- zero-day sentinel recall: {zd['sentinel_recall']}")
    lines.append(f"- adversarial holdout escape rate (frozen model): {adv}")
    lines.append(
        f"- drift hook: stable PSI {drift['stable']['psi']:.3f} (flag "
        f"{drift['stable']['flagged']}), injected-shift PSI "
        f"{drift['injected_shift']['psi']:.3f} (flag {drift['injected_shift']['flagged']})"
    )
    lines.append(f"- fidelity discriminator AUC (fallback): {fidelity['discriminator_auc']}")
    lines.append("")
    lines.append("## Sensitivity tornado (+/-50%)")
    lines.append("")
    lines.append("![tornado](sensitivity_tornado.png)")
    (out / "evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "evaluation_report.md"
