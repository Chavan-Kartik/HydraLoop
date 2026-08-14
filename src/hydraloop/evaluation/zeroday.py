"""Zero-day and adversarial-holdout evaluation.

Two distinct questions get two distinct numbers: the supervised stack's recall on
attack families held out of training, and the legit-only sentinel's recall on the
same holdout. The adversarial-holdout number freezes the model and reports how
much of the red team's evolved best still settles against it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..blue.features import mature_mask, true_labels
from ..evaluation.metrics import threshold_at_fpr


def _recall_at_fpr_threshold(scores_legit: np.ndarray, scores_fraud: np.ndarray,
                             fpr_target: float) -> float:
    if len(scores_legit) == 0 or len(scores_fraud) == 0:
        return float("nan")
    thr = threshold_at_fpr(np.zeros(len(scores_legit), dtype=int), scores_legit, fpr_target)
    return float(np.mean(scores_fraud >= thr))


def zeroday_split(
    supervised_score: callable,
    sentinel_score: callable,
    legit_ref: pd.DataFrame,
    holdout: pd.DataFrame,
    fpr_target: float = 0.01,
) -> dict:
    """Supervised vs sentinel recall on the zero-day holdout, reported separately."""
    legit = legit_ref[mature_mask(legit_ref) & (~true_labels(legit_ref).astype(bool))]
    fraud = holdout[mature_mask(holdout) & (true_labels(holdout).astype(bool))]
    if legit.empty or fraud.empty:
        return {"supervised_recall": None, "sentinel_recall": None}
    return {
        "supervised_recall": _recall_at_fpr_threshold(
            supervised_score(legit), supervised_score(fraud), fpr_target
        ),
        "sentinel_recall": _recall_at_fpr_threshold(
            sentinel_score(legit), sentinel_score(fraud), fpr_target
        ),
    }


def adversarial_escape_rate(frozen_score: callable, legit_ref: pd.DataFrame,
                            adversarial_fraud: pd.DataFrame, fpr_target: float = 0.01) -> float:
    """Fraction of the red team's evolved fraud that evades a frozen model."""
    legit = legit_ref[mature_mask(legit_ref) & (~true_labels(legit_ref).astype(bool))]
    fraud = adversarial_fraud[mature_mask(adversarial_fraud) & true_labels(adversarial_fraud).astype(bool)]
    if legit.empty or fraud.empty:
        return float("nan")
    recall = _recall_at_fpr_threshold(frozen_score(legit), frozen_score(fraud), fpr_target)
    if np.isnan(recall):
        return float("nan")
    return float(1.0 - recall)
