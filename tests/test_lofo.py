"""Integration test for the LOFO transfer matrix and zero-day split."""

from __future__ import annotations

from hydraloop.blue.detector import Detector
from hydraloop.blue.models.sentinel import SentinelModel
from hydraloop.evaluation.lofo import build_family_frames, transfer_matrix
from hydraloop.evaluation.zeroday import zeroday_split


def test_transfer_matrix_is_square_and_exposes_cells(small_config):
    legit_df, family_frauds = build_family_frames(small_config, fraud_per_family=40)
    result = transfer_matrix(legit_df, family_frauds, seed=small_config.simulation.seed)
    n = len(result["families"])
    assert n >= 2
    assert len(result["matrix"]) == n
    assert all(len(row) == n for row in result["matrix"])
    # weak_cells is a list (possibly empty) of off-diagonal low-transfer entries.
    assert isinstance(result["weak_cells"], list)


def test_zeroday_split_reports_two_numbers(small_config):
    import pandas as pd

    legit_df, family_frauds = build_family_frames(small_config, fraud_per_family=40)
    mixed = pd.concat([legit_df, *family_frauds.values()], ignore_index=True).sort_values("ts")
    cut = int(len(mixed) * 0.8)
    train, val = mixed.iloc[:cut], mixed.iloc[cut:]
    detector = Detector(seed=7).fit(train, val)
    sentinel = SentinelModel(seed=7).fit(train)

    # Use one family as a stand-in "unseen" holdout for the split mechanics.
    holdout = list(family_frauds.values())[0]
    result = zeroday_split(detector.score, sentinel.predict_proba, val, holdout)
    assert "supervised_recall" in result and "sentinel_recall" in result
