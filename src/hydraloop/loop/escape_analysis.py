"""Cluster the fraud that escaped, and label each cluster by its gene pattern.

An escape is a fraudulent transaction the live policy let settle. Grouping
escapes into behavioural clusters and naming them after the dominant attack
family turns "we missed 40 frauds" into "we have a new social-engineering escape
mode", which is what drives targeted retraining.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..blue.features import MODEL_FEATURES


@dataclass
class EscapeCluster:
    cluster_id: int
    size: int
    dominant_family: str
    dominant_attack_id: str
    gene_pattern: dict[str, float]
    txn_ids: list[str] = field(default_factory=list)


def escaped_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Fraud that the policy approved (attacker success)."""
    return df[(df["is_fraud"]) & (df["approved"])].reset_index(drop=True)


def cluster_escapes(df: pd.DataFrame, k_max: int = 4, seed: int = 42) -> list[EscapeCluster]:
    esc = escaped_frame(df)
    if esc.empty:
        return []
    X = esc[MODEL_FEATURES].astype(float).fillna(0.0).to_numpy()
    k = int(min(k_max, max(1, len(esc) // 8 or 1)))
    if k == 1 or len(esc) < 4:
        labels = np.zeros(len(esc), dtype=int)
    else:
        from sklearn.cluster import KMeans

        std = X.std(axis=0)
        std[std == 0] = 1.0
        labels = KMeans(n_clusters=k, random_state=seed, n_init=5).fit_predict((X - X.mean(0)) / std)

    clusters: list[EscapeCluster] = []
    for cid in sorted(set(labels.tolist())):
        rows = esc[labels == cid]
        fam = str(rows["attack_id"].fillna("unknown").mode().iloc[0]) if len(rows) else "unknown"
        family = str(rows["genome_id"].fillna("unknown").mode().iloc[0]) if len(rows) else "unknown"
        pattern = {f: float(rows[f].astype(float).mean()) for f in MODEL_FEATURES}
        clusters.append(
            EscapeCluster(
                cluster_id=int(cid),
                size=int(len(rows)),
                dominant_family=family,
                dominant_attack_id=fam,
                gene_pattern=pattern,
                txn_ids=[str(t) for t in rows["txn_id"].tolist()],
            )
        )
    return clusters
