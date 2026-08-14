"""An Isolation Forest sentinel trained on legitimate traffic only.

The supervised models can only catch what resembles past fraud. The sentinel
never sees a single fraud label in training; it learns the shape of normal and
flags departures from it. Its value is measured on the zero-day holdout and
reported separately, because that number answers "how do you catch what you
have never seen".
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..features import feature_matrix, mature_mask, true_labels


class SentinelModel:
    def __init__(self, seed: int = 42) -> None:
        self.model = IsolationForest(n_estimators=200, contamination="auto", random_state=seed)
        self._lo = 0.0
        self._hi = 1.0

    def fit(self, train_df: pd.DataFrame) -> SentinelModel:
        # Legit-only: mature rows that ground truth confirms are not fraud.
        mask = mature_mask(train_df) & (~true_labels(train_df).astype(bool))
        legit = train_df[mask]
        X = feature_matrix(legit)
        X = np.nan_to_num(X, nan=0.0)
        self.model.fit(X)
        raw = -self.model.score_samples(X)  # higher = more anomalous
        self._lo, self._hi = float(raw.min()), float(raw.max())
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        X = np.nan_to_num(feature_matrix(df), nan=0.0)
        raw = -self.model.score_samples(X)
        span = max(1e-9, self._hi - self._lo)
        return np.clip((raw - self._lo) / span, 0.0, 1.0)
