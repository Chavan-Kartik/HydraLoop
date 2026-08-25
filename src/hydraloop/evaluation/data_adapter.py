"""Bridge synthetic traffic to an external reference for a credibility check.

The lab is synthetic by design, so the honest question a reviewer asks is "how do
you know it resembles reality?". This module answers it two ways without ever
requiring credentials or a network:

1. Synthetic-shift mode. A second, differently seeded population is treated as
   the "real" reference. We report a discriminator AUC (near 0.5 means the two
   are hard to tell apart) and a TSTR / TRTS pair (train on one, test on the
   other) to show the detector transfers across the shift.

2. External-CSV mode. Any transaction CSV with at least an amount, a timestamp,
   and a fraud label is normalised into the fidelity feature space. We report
   the discriminator AUC and per-feature KS / Wasserstein divergences on the
   columns the two sources share. TSTR is only attempted when the external file
   already carries the full model feature set, and is reported as null with a
   reason otherwise rather than fabricated.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..blue.features import MODEL_FEATURES, mature_mask, true_labels
from ..config import Config
from .fidelity import discriminator_auc, marginal_divergences
from .metrics import threshold_at_fpr


@dataclass(frozen=True)
class ColumnMap:
    """How external column names map onto the canonical fields we need."""

    amount: str = "amount"
    timestamp: str = "timestamp"
    is_fraud: str = "is_fraud"
    amount_is_minor: bool = False  # if False, amounts are major units and get scaled
    # How to read the timestamp column: a parseable datetime string, or a numeric
    # offset (seconds/hours) from ``epoch`` -- real datasets use all three.
    timestamp_kind: str = "datetime"  # datetime | epoch_seconds | epoch_hours
    epoch: str = "2013-01-01"


# Built-in presets for well-known public fraud datasets, so a judge can point
# ``bench --preset sparkov`` at a downloaded file without hand-mapping columns.
DATASET_PRESETS: dict[str, ColumnMap] = {
    # Sparkov / "Credit Card Transactions Fraud Detection" (named fields).
    "sparkov": ColumnMap(amount="amt", timestamp="trans_date_trans_time", is_fraud="is_fraud"),
    # PaySim synthetic mobile-money (A2A-style); step is an hour index.
    "paysim": ColumnMap(amount="amount", timestamp="step", is_fraud="isFraud",
                        timestamp_kind="epoch_hours"),
    # ULB "Credit Card Fraud Detection" (PCA features; Time is seconds offset).
    "creditcard": ColumnMap(amount="Amount", timestamp="Time", is_fraud="Class",
                           timestamp_kind="epoch_seconds"),
}


def _mixed_frame(cfg: Config, fraud_per_family: int) -> pd.DataFrame:
    """A single legit+fraud transaction frame produced by the twin."""
    from .lofo import build_family_frames

    legit_df, family_frauds = build_family_frames(cfg, fraud_per_family=fraud_per_family)
    frames = [legit_df, *family_frauds.values()]
    return pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)


def _shifted_config(cfg: Config, seed_delta: int) -> Config:
    """Re-draw the twin under a different seed. The priors are NOT changed.

    Worth being blunt about, because it bounds what the fallback benchmark can
    claim: the reference it produces is another sample from the same generative
    process, so a discriminator failing to separate them shows the simulator is
    stationary and reproducible. It is not evidence of resemblance to real payment
    data, and must never be reported as such. Only ``--csv``/``--preset`` mode,
    against a licensed external dataset, measures realism.
    """
    sim = dataclasses.replace(cfg.simulation, seed=cfg.simulation.seed + seed_delta)
    return dataclasses.replace(cfg, simulation=sim)


def synthetic_and_reference(
    cfg: Config, fraud_per_family: int = 40, seed_delta: int = 101
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two twin populations: the lab's own, and a shifted one used as 'real'."""
    synthetic = _mixed_frame(cfg, fraud_per_family)
    reference = _mixed_frame(_shifted_config(cfg, seed_delta), fraud_per_family)
    return synthetic, reference


def _parse_timestamp(col: pd.Series, colmap: ColumnMap) -> pd.Series:
    """Read a timestamp column as datetime or as a numeric offset from an epoch."""
    if colmap.timestamp_kind == "epoch_seconds":
        base = pd.Timestamp(colmap.epoch)
        return base + pd.to_timedelta(pd.to_numeric(col, errors="coerce"), unit="s")
    if colmap.timestamp_kind == "epoch_hours":
        base = pd.Timestamp(colmap.epoch)
        return base + pd.to_timedelta(pd.to_numeric(col, errors="coerce"), unit="h")
    return pd.to_datetime(col, errors="coerce")


def load_external_csv(path: str | Path, colmap: ColumnMap | None = None) -> pd.DataFrame:
    """Normalise an arbitrary transaction CSV into the fidelity feature space."""
    colmap = colmap or ColumnMap()
    raw = pd.read_csv(path)
    for needed in (colmap.amount, colmap.timestamp, colmap.is_fraud):
        if needed not in raw.columns:
            raise ValueError(f"external CSV missing required column '{needed}'")

    amount = raw[colmap.amount].astype(float)
    if not colmap.amount_is_minor:
        amount = amount * 100.0
    ts = _parse_timestamp(raw[colmap.timestamp], colmap)

    out = pd.DataFrame(
        {
            "amount_minor": amount,
            "hour_of_day": ts.dt.hour.astype(float),
            "day_of_week": ts.dt.dayofweek.astype(float),
            "is_fraud": raw[colmap.is_fraud].astype(int).astype(bool),
        }
    )
    # Pass through any columns that already match a model feature name verbatim.
    for col in MODEL_FEATURES:
        if col not in out.columns and col in raw.columns:
            out[col] = pd.to_numeric(raw[col], errors="coerce")
    return out.dropna(subset=["amount_minor"]).reset_index(drop=True)


def _has_full_features(df: pd.DataFrame) -> bool:
    return all(c in df.columns for c in MODEL_FEATURES) and {"settled", "censored", "disputed"} <= set(df.columns)


def _recall_across(train_df: pd.DataFrame, test_df: pd.DataFrame, seed: int, fpr: float) -> float | None:
    """Fit a detector on train_df, report recall at fixed FPR on test_df."""
    if not (_has_full_features(train_df) and _has_full_features(test_df)):
        return None
    train = train_df.sort_values("ts") if "ts" in train_df else train_df
    cut = int(len(train) * 0.85)
    detector = Detector(seed=seed).fit(train.iloc[:cut], train.iloc[cut:])

    legit = test_df[mature_mask(test_df) & (~true_labels(test_df).astype(bool))]
    fraud = test_df[mature_mask(test_df) & true_labels(test_df).astype(bool)]
    if legit.empty or fraud.empty:
        return None
    legit_scores = detector.score(legit)
    thr = threshold_at_fpr(np.zeros(len(legit_scores), dtype=int), legit_scores, fpr)
    return float(np.mean(detector.score(fraud) >= thr))


def benchmark(
    synthetic_df: pd.DataFrame, reference_df: pd.DataFrame, seed: int = 42, fpr: float = 0.01
) -> dict:
    """Fidelity and transfer metrics between synthetic traffic and a reference."""
    overlap = [c for c in MODEL_FEATURES if c in synthetic_df.columns and c in reference_df.columns]
    result: dict = {
        "n_synthetic": int(len(synthetic_df)),
        "n_reference": int(len(reference_df)),
        "shared_feature_count": len(overlap),
        "discriminator_auc": discriminator_auc(reference_df, synthetic_df),
        "marginal_divergences": marginal_divergences(reference_df, synthetic_df),
    }

    if _has_full_features(reference_df):
        result["tstr_recall_at_fpr_1pct"] = _recall_across(synthetic_df, reference_df, seed, fpr)
        result["trts_recall_at_fpr_1pct"] = _recall_across(reference_df, synthetic_df, seed, fpr)
        result["transfer_note"] = "TSTR trains on synthetic and tests on the reference; TRTS is the reverse."
    else:
        result["tstr_recall_at_fpr_1pct"] = None
        result["trts_recall_at_fpr_1pct"] = None
        result["transfer_note"] = (
            "External source lacks the full point-in-time feature set; only "
            "distribution fidelity (discriminator, marginals) is computed."
        )
    return result


def _interpret(auc: float | None) -> str:
    if auc is None or np.isnan(auc):
        return "not enough overlapping rows to score"
    if auc <= 0.6:
        return "hard to distinguish from the reference (strong marginal fidelity)"
    if auc <= 0.8:
        return "partially distinguishable; some marginals differ"
    return "easily distinguished; marginals diverge from the reference"


def resolve_dataset(
    preset: str | None, csv: str | Path | None
) -> tuple[Path | None, ColumnMap | None, str]:
    """Resolve a ``--preset``/``--csv`` request into a path, column map, and note.

    A preset looks for ``data/external/<preset>.csv`` unless an explicit ``csv`` is
    given. When the file is absent we return ``None`` so the caller degrades to
    synthetic-shift instead of crashing the demo.
    """
    from ..paths import DATA_DIR

    if preset:
        colmap = DATASET_PRESETS.get(preset)
        if colmap is None:
            return None, None, f"unknown preset '{preset}'; using synthetic shift"
        path = Path(csv) if csv else DATA_DIR / "external" / f"{preset}.csv"
        if not path.exists():
            return None, colmap, (
                f"dataset '{preset}' not found at {path}; using synthetic shift "
                f"(drop the CSV there to benchmark against real data)"
            )
        return path, colmap, f"benchmarking against real dataset '{preset}' ({path.name})"
    if csv:
        path = Path(csv)
        if not path.exists():
            return None, None, f"csv {path} not found; using synthetic shift"
        return path, None, f"benchmarking against {path.name}"
    return None, None, "no external dataset supplied; using synthetic shift"


def run_data_benchmark(
    cfg: Config,
    external_csv: str | Path | None = None,
    colmap: ColumnMap | None = None,
    out_dir: Path | None = None,
    fraud_per_family: int = 40,
    preset: str | None = None,
) -> dict:
    """Run the credibility benchmark and write a JSON + Markdown report."""
    synthetic = _mixed_frame(cfg, fraud_per_family)

    note = ""
    if preset is not None or external_csv is not None:
        resolved_path, resolved_map, note = resolve_dataset(preset, external_csv)
        if resolved_path is not None:
            external_csv = resolved_path
            colmap = colmap or resolved_map
        else:
            external_csv = None  # degrade to synthetic shift

    if external_csv is not None:
        reference = load_external_csv(external_csv, colmap)
        mode = f"external_csv:{Path(external_csv).name}"
        reference_source = Path(external_csv).name
    else:
        reference = _mixed_frame(_shifted_config(cfg, 101), fraud_per_family)
        mode = "synthetic_shift"
        reference_source = "synthetic_shift"

    report = benchmark(synthetic, reference, seed=cfg.simulation.seed)
    report["mode"] = mode
    report["reference_source"] = reference_source
    report["interpretation"] = _interpret(report.get("discriminator_auc"))
    report["measures_realism"] = mode.startswith("external_csv")
    report["claim"] = (
        "distinguishability from a real reference dataset"
        if mode.startswith("external_csv")
        else "stationarity across independent draws of the same generator; this is "
        "NOT a measurement of resemblance to real payment data"
    )
    if note:
        report["note"] = note

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "data_benchmark.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        (out_dir / "data_benchmark.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _render_markdown(report: dict) -> str:
    auc = report.get("discriminator_auc")
    lines = ["# Data credibility benchmark", ""]
    lines.append(f"- mode: {report['mode']}")
    lines.append(f"- synthetic rows: {report['n_synthetic']}")
    lines.append(f"- reference rows: {report['n_reference']}")
    lines.append(f"- shared model features: {report['shared_feature_count']}")
    auc_str = "n/a" if auc is None or np.isnan(auc) else f"{auc:.3f}"
    lines.append(f"- discriminator AUC: {auc_str} ({_interpret(auc)})")
    tstr = report.get("tstr_recall_at_fpr_1pct")
    trts = report.get("trts_recall_at_fpr_1pct")
    lines.append(f"- TSTR recall @1% FPR: {'n/a' if tstr is None else f'{tstr:.3f}'}")
    lines.append(f"- TRTS recall @1% FPR: {'n/a' if trts is None else f'{trts:.3f}'}")
    lines.append(f"- {report['transfer_note']}")
    lines.append("")
    lines.append("## Marginal divergences (lower is closer)")
    lines.append("")
    lines.append("| feature | KS | Wasserstein |")
    lines.append("|---|---:|---:|")
    for row in report.get("marginal_divergences", []):
        lines.append(f"| {row['feature']} | {row['ks']:.4f} | {row['wasserstein']:.2f} |")
    return "\n".join(lines) + "\n"


def make_demo_reference_csv(path: str | Path, cfg: Config, fraud_per_family: int = 20) -> Path:
    """Write a stand-in external CSV from a shifted twin run.

    This is a demonstration fixture, not real payment data: it lets the external
    CSV path run offline. Point ``--csv`` at a genuine dataset to benchmark it.
    """
    ref = _mixed_frame(_shifted_config(cfg, 202), fraud_per_family)
    epoch = pd.Timestamp("2020-01-01")
    ts = epoch + pd.to_timedelta(ref["ts"].astype(float), unit="s")
    frame = pd.DataFrame(
        {
            "amount": ref["amount_minor"].astype(float) / 100.0,
            "timestamp": ts.dt.strftime("%Y-%m-%d %H:%M:%S"),
            "is_fraud": ref["is_fraud"].astype(int),
        }
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path
