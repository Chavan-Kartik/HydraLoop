"""The regression gauntlet: a candidate model must not regress on the archive.

Recall is measured at a fixed operating FPR set on held-out legit traffic, then
evaluated on every historical escape. A candidate is promoted only if it holds
recall on the archive, stays inside the FPR budget, and stays calibrated;
otherwise the incumbent stands and the swap is rolled back atomically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..evaluation.metrics import expected_calibration_error


@dataclass
class GauntletResult:
    promote: bool
    reason: str
    incumbent_recall: float
    candidate_recall: float
    candidate_fpr: float
    candidate_ece: float
    metrics: dict = field(default_factory=dict)


def _threshold_at_fpr(scores: np.ndarray, fpr_target: float) -> float:
    """Lowest threshold whose realised FPR stays inside the budget.

    A plain ``quantile`` is wrong here: isotonic calibration maps many rows onto
    the same value, so the quantile lands mid-plateau and ``scores >= threshold``
    then flags every tied row -- several times the intended budget. Walking the
    unique values instead keeps the operating point inside the budget by
    construction, at the cost of being conservative when a plateau straddles it.
    """
    if len(scores) == 0:
        return 0.5
    unique = np.unique(scores)
    for candidate in unique:
        if float(np.mean(scores >= candidate)) <= fpr_target:
            return float(candidate)
    return float(np.nextafter(unique[-1], np.inf))


def _recall_at_threshold(detector: Detector, fraud_df: pd.DataFrame, thr: float) -> float:
    if fraud_df.empty:
        return 0.0
    scores = detector.score(fraud_df)
    return float(np.mean(scores >= thr))


def run_gauntlet(
    incumbent: Detector | None,
    candidate: Detector,
    legit_val_df: pd.DataFrame,
    archive_fraud_df: pd.DataFrame,
    fpr_target: float = 0.01,
    ece_max: float = 0.15,
    recall_tolerance: float = 0.02,
) -> GauntletResult:
    cand_legit = candidate.score(legit_val_df) if len(legit_val_df) else np.array([])
    cand_thr = _threshold_at_fpr(cand_legit, fpr_target)
    cand_recall = _recall_at_threshold(candidate, archive_fraud_df, cand_thr)
    cand_fpr = float(np.mean(cand_legit >= cand_thr)) if len(cand_legit) else 0.0

    combined = pd.concat([legit_val_df, archive_fraud_df], ignore_index=True)
    cand_scores = candidate.score(combined) if len(combined) else np.array([])
    y = combined["is_fraud"].astype(int).to_numpy() if len(combined) else np.array([])
    cand_ece = float(expected_calibration_error(y, cand_scores)[0]) if len(y) else 0.0

    if incumbent is None:
        return GauntletResult(
            promote=True,
            reason="generation-1 bootstrap: no incumbent to protect",
            incumbent_recall=0.0,
            candidate_recall=cand_recall,
            candidate_fpr=cand_fpr,
            candidate_ece=cand_ece,
            metrics={"threshold": cand_thr},
        )

    inc_legit = incumbent.score(legit_val_df) if len(legit_val_df) else np.array([])
    inc_thr = _threshold_at_fpr(inc_legit, fpr_target)
    inc_recall = _recall_at_threshold(incumbent, archive_fraud_df, inc_thr)

    regressed = cand_recall < inc_recall - recall_tolerance
    over_fpr = cand_fpr > fpr_target * 1.5
    miscalibrated = cand_ece > ece_max

    if regressed:
        reason = (
            f"REJECT: archive recall regressed {inc_recall:.3f} -> {cand_recall:.3f} "
            f"(tolerance {recall_tolerance})"
        )
        promote = False
    elif over_fpr:
        reason = f"REJECT: FPR {cand_fpr:.4f} exceeds budget {fpr_target * 1.5:.4f}"
        promote = False
    elif miscalibrated:
        reason = f"REJECT: ECE {cand_ece:.3f} exceeds {ece_max}"
        promote = False
    else:
        reason = f"PROMOTE: archive recall {inc_recall:.3f} -> {cand_recall:.3f}, FPR {cand_fpr:.4f}"
        promote = True

    return GauntletResult(
        promote=promote,
        reason=reason,
        incumbent_recall=inc_recall,
        candidate_recall=cand_recall,
        candidate_fpr=cand_fpr,
        candidate_ece=cand_ece,
        metrics={"inc_threshold": inc_thr, "cand_threshold": cand_thr},
    )


class ModelRegistry:
    """Points at the live detector; promotion is an atomic file replace."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.incumbent: Detector | None = None

    def promote(self, candidate: Detector) -> None:
        tmp = self.path.with_suffix(".pkl.tmp")
        candidate.save(tmp)
        os.replace(tmp, self.path)  # atomic on POSIX and Windows
        self.incumbent = candidate

    def rollback(self) -> None:
        # No-op by design: the incumbent file was never overwritten.
        return None
