"""Detection metrics chosen for a rare-event, cost-sensitive problem.

Accuracy and plain ROC-AUC are misleading at sub-1% prevalence, so the primary
metric is PR-AUC, complemented by recall at fixed low FPR, precision at review
capacity, value-detection-rate (share of fraudulent *value* stopped), and ECE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass
class ReliabilityCurve:
    bin_confidence: list[float]
    bin_accuracy: list[float]
    bin_count: list[int]


def pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(average_precision_score(y_true, scores))


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, scores))


def threshold_at_fpr(y_true: np.ndarray, scores: np.ndarray, target_fpr: float) -> float:
    neg = scores[y_true == 0]
    if neg.size == 0:
        return 1.0
    # The score exceeded by exactly target_fpr of negatives.
    return float(np.quantile(neg, 1.0 - target_fpr))


def recall_at_fpr(y_true: np.ndarray, scores: np.ndarray, target_fpr: float) -> float:
    thr = threshold_at_fpr(y_true, scores, target_fpr)
    pos = scores[y_true == 1]
    if pos.size == 0:
        return float("nan")
    return float((pos >= thr).mean())


def precision_at_capacity(y_true: np.ndarray, scores: np.ndarray, capacity: int) -> float:
    if capacity <= 0:
        return float("nan")
    order = np.argsort(-scores)
    top = order[: min(capacity, len(order))]
    if top.size == 0:
        return float("nan")
    return float(y_true[top].mean())


def value_detection_rate(
    y_true: np.ndarray, scores: np.ndarray, value: np.ndarray, target_fpr: float
) -> float:
    thr = threshold_at_fpr(y_true, scores, target_fpr)
    fraud_value = value[y_true == 1]
    if fraud_value.sum() <= 0:
        return float("nan")
    stopped = value[(y_true == 1) & (scores >= thr)].sum()
    return float(stopped / fraud_value.sum())


def expected_calibration_error(
    y_true: np.ndarray, prob: np.ndarray, n_bins: int = 10
) -> tuple[float, ReliabilityCurve]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    conf, acc, cnt = [], [], []
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (prob >= lo) & (prob < hi) if i < n_bins - 1 else (prob >= lo) & (prob <= hi)
        if not mask.any():
            conf.append((lo + hi) / 2)
            acc.append(0.0)
            cnt.append(0)
            continue
        bin_conf = float(prob[mask].mean())
        bin_acc = float(y_true[mask].mean())
        conf.append(bin_conf)
        acc.append(bin_acc)
        cnt.append(int(mask.sum()))
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece), ReliabilityCurve(conf, acc, cnt)


def expected_calibration_error_equal_mass(
    y_true: np.ndarray, prob: np.ndarray, n_bins: int = 10
) -> float:
    """Adaptive (equal-frequency) ECE, more stable under heavy class imbalance."""
    n = len(prob)
    if n == 0:
        return float("nan")
    order = np.argsort(prob)
    y2, p2 = y_true[order], prob[order]
    ece = 0.0
    for chunk in np.array_split(np.arange(n), n_bins):
        if chunk.size == 0:
            continue
        ece += (chunk.size / n) * abs(y2[chunk].mean() - p2[chunk].mean())
    return float(ece)


def full_report(
    y_true: np.ndarray,
    scores: np.ndarray,
    value: np.ndarray,
    review_capacity: int,
    prob: np.ndarray | None = None,
) -> dict:
    prob = scores if prob is None else prob
    ece, curve = expected_calibration_error(y_true, prob)
    ece_mass = expected_calibration_error_equal_mass(y_true, prob)
    return {
        "ece_equal_mass": ece_mass,
        "pr_auc": pr_auc(y_true, scores),
        "roc_auc": roc_auc(y_true, scores),
        "recall_at_fpr_0.1pct": recall_at_fpr(y_true, scores, 0.001),
        "recall_at_fpr_0.5pct": recall_at_fpr(y_true, scores, 0.005),
        "recall_at_fpr_1pct": recall_at_fpr(y_true, scores, 0.01),
        "precision_at_capacity": precision_at_capacity(y_true, scores, review_capacity),
        "value_detection_rate_at_fpr_1pct": value_detection_rate(y_true, scores, value, 0.01),
        "ece": ece,
        "reliability": {
            "confidence": curve.bin_confidence,
            "accuracy": curve.bin_accuracy,
            "count": curve.bin_count,
        },
    }
