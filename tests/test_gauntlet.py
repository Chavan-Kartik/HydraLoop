import numpy as np
import pandas as pd

from hydraloop.loop.gauntlet import run_gauntlet


class _Fake:
    """A stand-in detector that scores by a per-row column."""

    def __init__(self, col: str):
        self.col = col

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return df[self.col].astype(float).to_numpy()


def _legit(n=200):
    rng = np.random.default_rng(0)
    return pd.DataFrame({"is_fraud": False, "good_score": rng.uniform(0, 0.2, n),
                         "bad_score": rng.uniform(0, 0.2, n)})


def _fraud(n=100):
    return pd.DataFrame({"is_fraud": True, "good_score": np.full(n, 0.9),
                         "bad_score": np.full(n, 0.05)})


def test_bootstrap_promotes_without_incumbent():
    res = run_gauntlet(None, _Fake("good_score"), _legit(), _fraud())
    assert res.promote
    assert "bootstrap" in res.reason


def test_regressed_candidate_is_rejected():
    incumbent = _Fake("good_score")  # catches fraud
    candidate = _Fake("bad_score")   # forgot the archive
    res = run_gauntlet(incumbent, candidate, _legit(), _fraud())
    assert not res.promote
    assert "regressed" in res.reason
    assert res.candidate_recall < res.incumbent_recall


def test_good_candidate_promoted():
    res = run_gauntlet(_Fake("good_score"), _Fake("good_score"), _legit(), _fraud())
    assert res.promote
