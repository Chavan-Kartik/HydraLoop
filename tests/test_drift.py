import numpy as np

from hydraloop.evaluation.drift import DriftMonitor, kl_divergence, psi


def test_no_drift_is_near_zero():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    cur = rng.normal(0, 1, 5000)
    assert psi(ref, cur) < 0.1
    assert kl_divergence(ref, cur) < 0.1


def test_shift_raises_psi_and_flags():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    shifted = rng.normal(3, 1, 5000)
    monitor = DriftMonitor(reference=ref)
    result = monitor.check(shifted)
    assert result["psi"] > 0.2
    assert result["flagged"] is True


def test_psi_is_non_negative():
    rng = np.random.default_rng(1)
    ref = rng.gamma(2, 2, 3000)
    cur = rng.gamma(2, 2.5, 3000)
    assert psi(ref, cur) >= 0.0
