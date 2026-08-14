"""Population-stability and KL monitoring for drift on legitimate behaviour.

Fraud models degrade when *legitimate* behaviour shifts under them, not only when
attacks change. This monitor compares a live feature distribution against a frozen
reference and flags drift by Population Stability Index and KL divergence, so a
retrain can be triggered before the false-positive rate quietly climbs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-6


def _binned_proportions(reference: np.ndarray, current: np.ndarray, bins: int):
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_p = ref_counts / max(1, ref_counts.sum())
    cur_p = cur_counts / max(1, cur_counts.sum())
    return np.clip(ref_p, _EPS, None), np.clip(cur_p, _EPS, None)


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref_p, cur_p = _binned_proportions(reference, current, bins)
    return float(np.sum((cur_p - ref_p) * np.log(cur_p / ref_p)))


def kl_divergence(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref_p, cur_p = _binned_proportions(reference, current, bins)
    return float(np.sum(cur_p * np.log(cur_p / ref_p)))


@dataclass
class DriftMonitor:
    reference: np.ndarray
    bins: int = 10
    psi_threshold: float = 0.2  # the conventional "material shift" line

    def check(self, current: np.ndarray) -> dict:
        p = psi(self.reference, current, self.bins)
        k = kl_divergence(self.reference, current, self.bins)
        return {"psi": p, "kl": k, "flagged": bool(p > self.psi_threshold)}
