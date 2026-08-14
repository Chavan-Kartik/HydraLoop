"""Isotonic probability calibration.

The policy layer minimises expected loss, which only makes sense if the scores
are true probabilities. Calibration is fit on a held-out fold, and its quality
is reported as ECE, not hidden.
"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


class IsotonicCalibrator:
    def __init__(self) -> None:
        self._iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._fitted = False

    def fit(self, scores: np.ndarray, y: np.ndarray) -> IsotonicCalibrator:
        if len(np.unique(y)) < 2:
            # Not enough signal to calibrate; fall back to identity.
            self._fitted = False
            return self
        self._iso.fit(scores, y)
        self._fitted = True
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        if not self._fitted:
            return np.clip(scores, 0.0, 1.0)
        return self._iso.predict(scores)
