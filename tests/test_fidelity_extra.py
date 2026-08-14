import numpy as np
import pandas as pd

from hydraloop.evaluation.fidelity import discriminator_auc, marginal_divergences


def _frame(mean, n=400, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "amount_minor": rng.normal(mean, 1000, n).clip(1),
            "velocity_24h": rng.poisson(2, n),
            "hour_of_day": rng.uniform(0, 24, n),
            "day_of_week": rng.integers(0, 7, n),
            "account_age_days": rng.uniform(0, 365, n),
        }
    )


def test_discriminator_near_half_for_same_distribution():
    a = _frame(10000, seed=1)
    b = _frame(10000, seed=2)
    auc = discriminator_auc(a, b)
    assert 0.35 <= auc <= 0.65  # indistinguishable draws


def test_discriminator_separates_shifted_distributions():
    a = _frame(10000, seed=1)
    b = _frame(80000, seed=2)  # very different amounts
    assert discriminator_auc(a, b) > 0.75


def test_marginals_report_ks_and_wasserstein():
    a = _frame(10000, seed=1)
    b = _frame(10000, seed=2)
    rows = marginal_divergences(a, b)
    assert any(r["feature"] == "amount_minor" for r in rows)
    for r in rows:
        assert r["ks"] >= 0.0 and r["wasserstein"] >= 0.0
