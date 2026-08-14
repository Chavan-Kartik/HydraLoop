"""LightGBM tabular detector with class-imbalance handling."""

from __future__ import annotations

import numpy as np
from lightgbm import LGBMClassifier

from ..features import MODEL_FEATURES


class TabularModel:
    def __init__(self, seed: int = 42) -> None:
        self.feature_names = list(MODEL_FEATURES)
        # No class_weight: rebalancing distorts predicted probabilities, and the
        # policy layer sets the operating threshold by expected loss. We keep the
        # scores honest and let isotonic calibration and the policy do the rest.
        self.model = LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            n_jobs=1,
            verbose=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> TabularModel:
        self.model.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if X.shape[0] == 0:
            return np.zeros(0, dtype=float)
        return self.model.predict_proba(X)[:, 1]
