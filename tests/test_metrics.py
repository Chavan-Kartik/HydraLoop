import numpy as np
import pytest

from hydraloop.evaluation.metrics import (
    confusion_at_threshold,
    expected_calibration_error,
    expected_calibration_error_equal_mass,
    pr_auc,
    precision_at_capacity,
    precision_at_prevalence,
    recall_at_fpr,
    threshold_at_fpr,
    value_detection_rate,
)


def test_pr_auc_perfect_separation():
    y = np.array([0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.8, 0.9])
    assert pr_auc(y, s) == 1.0


def test_recall_at_fpr_monotone():
    rng = np.random.default_rng(0)
    y = np.array([0] * 900 + [1] * 100)
    s = np.concatenate([rng.normal(0.3, 0.1, 900), rng.normal(0.7, 0.1, 100)])
    r1 = recall_at_fpr(y, s, 0.01)
    r5 = recall_at_fpr(y, s, 0.05)
    assert 0 <= r1 <= r5 <= 1


def test_precision_at_capacity_top_k():
    y = np.array([1, 0, 1, 0, 1])
    s = np.array([0.9, 0.1, 0.8, 0.2, 0.7])
    assert precision_at_capacity(y, s, 3) == 1.0


def test_value_detection_rate_counts_value_not_rows():
    y = np.array([1, 1, 0, 0])
    s = np.array([0.9, 0.1, 0.05, 0.05])
    value = np.array([1000.0, 10.0, 5.0, 5.0])
    # At a threshold catching only the high-score fraud, most fraud value stopped.
    vdr = value_detection_rate(y, s, value, target_fpr=0.5)
    assert vdr > 0.9


def test_ece_zero_when_perfectly_calibrated():
    y = np.array([0, 0, 1, 1] * 50)
    p = np.array([0.0, 0.0, 1.0, 1.0] * 50)
    ece, _ = expected_calibration_error(y, p)
    assert ece < 1e-9
    assert expected_calibration_error_equal_mass(y, p) < 1e-9


def test_confusion_cells_sum_to_population():
    y = np.array([0] * 90 + [1] * 10)
    s = np.concatenate([np.linspace(0.0, 0.5, 90), np.linspace(0.5, 1.0, 10)])
    c = confusion_at_threshold(y, s, 0.5)
    assert c["tp"] + c["fp"] + c["fn"] + c["tn"] == 100
    assert c["tp"] + c["fn"] == 10
    assert c["fp"] + c["tn"] == 90
    assert c["prevalence"] == 0.10


def test_confusion_f1_is_harmonic_mean_of_its_own_precision_and_recall():
    y = np.array([1, 1, 1, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.2, 0.7, 0.1, 0.1])
    c = confusion_at_threshold(y, s, 0.5)
    p, r = c["precision"], c["recall"]
    assert c["f1"] == pytest.approx(2 * p * r / (p + r))


def test_threshold_respects_budget_under_heavy_ties():
    """Isotonic calibration produces plateaus; a quantile would overshoot the budget."""
    y = np.zeros(1000, dtype=int)
    scores = np.full(1000, 0.42)
    scores[:5] = 0.99
    thr = threshold_at_fpr(y, scores, 0.01)
    assert float(np.mean(scores >= thr)) <= 0.01


def test_precision_falls_when_prevalence_falls():
    """The same detector looks far worse on a realistic base rate, and should."""
    high = precision_at_prevalence(recall=0.9, fpr=0.01, prevalence=0.09)
    low = precision_at_prevalence(recall=0.9, fpr=0.01, prevalence=0.005)
    assert high > low
    assert low == pytest.approx(0.9 * 0.005 / (0.9 * 0.005 + 0.01 * 0.995))
