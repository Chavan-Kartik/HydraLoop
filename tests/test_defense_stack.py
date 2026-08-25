"""Integration test for the Phase 8 defence stack and its ablation table."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hydraloop.blue.ensemble import BASE_ORDER, EnsembleDetector
from hydraloop.blue.features import mature_mask, true_labels
from hydraloop.blue.models.sentinel import SentinelModel
from hydraloop.evaluation.metrics import recall_at_fpr
from hydraloop.red.dsl import genome_from_template
from hydraloop.red.mixer import build_attack_specs
from hydraloop.twin.population import SECONDS_PER_DAY
from hydraloop.twin.run import build_engine, legit_session_specs


@pytest.fixture(scope="module")
def labelled_splits():
    """Splits large enough that a claim about model quality means something.

    Sized deliberately: at 1200 legitimate sessions the validation fold held 13
    positives and test held 4, which is too few to rank six models against each
    other -- the assertions below passed or failed on noise rather than on the
    stack actually working.
    """
    from hydraloop.config import Config, DefenderConfig, RedTeamConfig, SimulationConfig

    n_legit = 7000
    sim = SimulationConfig(
        seed=11, legitimate_transactions_per_generation=n_legit, horizon_days=60
    )
    cfg = Config(raw={}, simulation=sim, defender=DefenderConfig(), red_team=RedTeamConfig())
    engine, registry = build_engine(cfg)
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(cfg, engine, registry, n_legit)
    genomes = [
        genome_from_template("social_engineering", "AF-09", {}),
        genome_from_template("account_takeover", "AF-05", {}),
    ]
    fraud, _ = build_attack_specs(engine, registry, genomes, 700, horizon_s)
    df = pd.DataFrame(engine.simulate(legit + fraud).transactions).sort_values("ts").reset_index(drop=True)
    n = len(df)
    a, b = int(n * 0.7), int(n * 0.85)
    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()


def test_ensemble_fits_and_scores_in_unit_interval(labelled_splits):
    train, val, test = labelled_splits
    ens = EnsembleDetector(seed=11).fit(train, val)
    scores = ens.score(test)
    assert len(scores) == len(test)
    assert scores.min() >= 0.0 and scores.max() <= 1.0
    for name, s in ens.base_scores(test).items():
        assert name in BASE_ORDER
        assert s.min() >= 0.0 and s.max() <= 1.0


def test_ablation_table_lists_every_model_plus_ensemble(labelled_splits):
    train, val, test = labelled_splits
    ens = EnsembleDetector(seed=11).fit(train, val)
    table = ens.ablation_table(test)
    names = [r["model"] for r in table]
    assert names == list(BASE_ORDER) + ["ensemble"]
    # The ensemble should not be materially worse than the best single model.
    base_best = max(r["pr_auc_observed"] or 0.0 for r in table if r["model"] != "ensemble")
    ens_row = next(r for r in table if r["model"] == "ensemble")
    assert (ens_row["pr_auc_observed"] or 0.0) >= base_best - 0.1


def test_sentinel_trained_on_legit_only_reports_zeroday_recall(labelled_splits):
    train, val, test = labelled_splits
    sentinel = SentinelModel(seed=11).fit(train)
    ev = test[mature_mask(test)]
    y_true = true_labels(ev)
    scores = sentinel.predict_proba(ev)
    # It produces a usable anomaly score and a reportable solo recall number.
    assert scores.min() >= 0.0 and scores.max() <= 1.0
    if len(np.unique(y_true)) > 1:
        solo_recall = recall_at_fpr(y_true, scores, 0.01)
        assert 0.0 <= solo_recall <= 1.0
