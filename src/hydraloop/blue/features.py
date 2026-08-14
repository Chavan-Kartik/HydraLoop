"""Feature and label selection for the blue team.

Features are exactly the point-in-time snapshot the twin froze at decision time.
Any column produced after the decision (approval, capture, settlement, dispute)
is forbidden as a feature, which is what the leakage guard test enforces.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..twin.online import FEATURE_COLUMNS

MODEL_FEATURES = list(FEATURE_COLUMNS)

# Columns that describe what happened *after* the decision. Using any of these as
# a model input would be temporal leakage.
FORBIDDEN_FEATURES = frozenset(
    {
        "approved",
        "captured_minor",
        "settled",
        "settlement_ts",
        "disputed",
        "dispute_ts",
        "charged_back",
        "label_observed_at",
        "is_fraud",
        "action",
        "risk_score",
        "degraded",
    }
)


def feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[MODEL_FEATURES].astype(float).to_numpy()


def observed_labels(df: pd.DataFrame) -> np.ndarray:
    """The label a bank would eventually observe: a raised dispute."""
    return df["disputed"].astype(int).to_numpy()


def true_labels(df: pd.DataFrame) -> np.ndarray:
    """Ground truth, available only in simulation; used for evaluation."""
    return df["is_fraud"].astype(int).to_numpy()


def mature_mask(df: pd.DataFrame) -> np.ndarray:
    """Rows whose outcome had a chance to mature (settled and not censored).

    Immature rows are excluded from training rather than treated as clean
    negatives, because their label could still flip after the cutoff.
    """
    return ((df["settled"]) & (~df["censored"])).to_numpy()
