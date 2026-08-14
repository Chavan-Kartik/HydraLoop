"""A transparent velocity-rule baseline.

Its purpose is to anchor the ML result: a model that cannot beat a handful of
obvious rules is not earning its complexity. The score is a bounded blend of the
signals a fraud analyst would reach for first.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class VelocityRuleBaseline:
    def score(self, df: pd.DataFrame) -> np.ndarray:
        velocity = df["velocity_24h"].fillna(0).astype(float).to_numpy()
        payee_new = df["payee_is_new"].fillna(0).astype(float).to_numpy()
        device_new = df["device_is_new"].fillna(0).astype(float).to_numpy()
        balance_ratio = df["balance_ratio"].fillna(0).astype(float).clip(0, 1).to_numpy()
        z = df["amount_zscore"].fillna(0).astype(float).abs().clip(0, 5).to_numpy() / 5.0

        vel = np.clip(velocity / 10.0, 0, 1)
        raw = 0.30 * vel + 0.25 * payee_new + 0.15 * device_new + 0.15 * balance_ratio + 0.15 * z
        return np.clip(raw, 0.0, 1.0)
