"""The calibrated detector bundle used by the policy layer and the loop."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .calibration import IsotonicCalibrator
from .features import feature_matrix, mature_mask, observed_labels
from .models import TabularModel


class Detector:
    def __init__(self, seed: int = 42) -> None:
        self.model = TabularModel(seed=seed)
        self.calibrator = IsotonicCalibrator()

    def fit(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> Detector:
        tr = train_df[mature_mask(train_df)]
        self.model.fit(feature_matrix(tr), observed_labels(tr))
        val = val_df[mature_mask(val_df)]
        if len(val):
            raw = self.model.predict_proba(feature_matrix(val))
            self.calibrator.fit(raw, observed_labels(val))
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        raw = self.model.predict_proba(feature_matrix(df))
        return self.calibrator.transform(raw)

    def score_raw(self, df: pd.DataFrame) -> np.ndarray:
        """Uncalibrated model output, for choosing an operating threshold.

        Isotonic calibration is monotone, so it preserves ranking in principle, but
        fitted on a few thousand rows it is a step function with only a handful of
        distinct levels. That destroys resolution exactly where it matters -- among
        the highest-scoring rows -- so no threshold on the calibrated score can hit a
        1% FPR target: the nearest achievable operating points straddle it. Rank and
        threshold on this; use ``score`` for the expected-loss decision and for
        reporting calibration quality.
        """
        return self.model.predict_proba(feature_matrix(df))

    def score_row(self, features: dict[str, float | None]) -> float:
        row = np.array(
            [float(features.get(f) if features.get(f) is not None else np.nan)
             for f in self.model.feature_names]
        ).reshape(1, -1)
        raw = self.model.predict_proba(row)
        return float(self.calibrator.transform(raw)[0])

    def save(self, path: Path) -> Path:
        with open(path, "wb") as fh:
            pickle.dump(self, fh)
        return path

    @staticmethod
    def load(path: Path) -> Detector:
        with open(path, "rb") as fh:
            return pickle.load(fh)
