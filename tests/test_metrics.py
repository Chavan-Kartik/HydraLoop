import numpy as np

from hydraloop.evaluation.metrics import (
    expected_calibration_error,
    expected_calibration_error_equal_mass,
    pr_auc,
    precision_at_capacity,
    recall_at_fpr,
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
