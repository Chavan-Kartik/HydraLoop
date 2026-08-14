"""An abstract narrative/artefact classifier.

Per the abstraction policy, HydraLoop never handles real scam text. This model
instead reads the *behavioural narrative* of a transaction -- a discretised bag
of coercion/urgency cues (new payee, night-time, account-takeover-shaped
velocity, first-use device) -- and learns which narratives read as fraudulent.
It is deliberately distinct from the tabular model, which uses raw numerics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import LogisticRegression

from ..features import mature_mask, observed_labels


def _amount_bucket(z: float) -> str:
    if z is None or np.isnan(z):
        return "amtz_na"
    if z < 1:
        return "amtz_lo"
    if z < 3:
        return "amtz_mid"
    return "amtz_hi"


def _narrative_tokens(row) -> dict[str, float]:
    hour = (float(row["ts"]) / 3600.0) % 24.0
    vel = float(row.get("velocity_24h", 0.0))
    tokens = {
        f"chan_{int(row.get('channel_code', 0))}": 1.0,
        _amount_bucket(row.get("amount_zscore")): 1.0,
        f"newpayee_{int(row.get('payee_is_new', 0))}": 1.0,
        f"newdev_{int(row.get('device_is_new', 0))}": 1.0,
        f"night_{int(hour < 6 or hour >= 23)}": 1.0,
        f"accnew_{int(row.get('account_is_new', 0))}": 1.0,
        f"vel_{'hi' if vel >= 3 else 'lo'}": 1.0,
    }
    return tokens


class NarrativeModel:
    def __init__(self, seed: int = 42, n_features: int = 64) -> None:
        self.hasher = FeatureHasher(n_features=n_features, input_type="dict")
        self.head = LogisticRegression(max_iter=500)
        self.seed = seed

    def _matrix(self, df: pd.DataFrame):
        dicts = [_narrative_tokens(r) for _, r in df.iterrows()]
        return self.hasher.transform(dicts)

    def fit(self, train_df: pd.DataFrame) -> NarrativeModel:
        tr = train_df[mature_mask(train_df)]
        y = observed_labels(tr)
        if len(np.unique(y)) < 2:
            self._degenerate = True
            self._pos_rate = float(y.mean()) if len(y) else 0.0
            return self
        self._degenerate = False
        self.head.fit(self._matrix(tr), y)
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if getattr(self, "_degenerate", False):
            return np.full(len(df), self._pos_rate, dtype=float)
        return self.head.predict_proba(self._matrix(df))[:, 1]
