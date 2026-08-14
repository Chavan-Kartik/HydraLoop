"""SHAP-based reason codes for a single decision.

Reason codes turn a score into something an analyst can act on. A cheap
counterfactual on one high-signal gene-like feature accompanies them.
"""

from __future__ import annotations

import numpy as np

from .features import MODEL_FEATURES


def top_reason_codes(model, X_row: np.ndarray, k: int = 5) -> list[dict]:
    import shap

    explainer = shap.TreeExplainer(model.model)
    values = explainer.shap_values(X_row.reshape(1, -1))
    if isinstance(values, list):  # older SHAP returns per-class list
        values = values[-1]
    contrib = np.asarray(values).reshape(-1)
    order = np.argsort(-np.abs(contrib))[:k]
    return [
        {"feature": MODEL_FEATURES[i], "contribution": float(contrib[i])}
        for i in order
    ]


def counterfactual(
    model, calibrator, X_row: np.ndarray, feature: str, new_value: float
) -> dict:
    idx = MODEL_FEATURES.index(feature)
    before = float(calibrator.transform(model.predict_proba(X_row.reshape(1, -1)))[0])
    modified = X_row.copy()
    modified[idx] = new_value
    after = float(calibrator.transform(model.predict_proba(modified.reshape(1, -1)))[0])
    return {
        "feature": feature,
        "from_value": float(X_row[idx]),
        "to_value": float(new_value),
        "risk_before": before,
        "risk_after": after,
    }
