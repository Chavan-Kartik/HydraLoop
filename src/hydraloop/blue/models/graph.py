"""Graph detector: structural GraphSAGE embeddings plus a learned head.

Embeddings come from time-sliced point-in-time snapshots -- a row is embedded
using the snapshot built from edges strictly before the slice it falls in, so a
transaction never sees its own or later edges. The mean-pool aggregation is the
structural GraphSAGE; a logistic head learns the fraud mapping on top. Keeping
the aggregation unparameterised removes a whole class of training instability
while still exposing fan-in / fan-out structure that mule networks create.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression

from ..features import mature_mask, observed_labels
from ..graph.snapshot import GraphSnapshot, _node_key, build_snapshot

_N_SLICES = 6


class GraphSAGEModel:
    def __init__(self, seed: int = 42, layers: int = 2) -> None:
        self.seed = seed
        self.layers = layers
        self.head = LogisticRegression(max_iter=500, C=1.0)
        self.node_universe: list[str] = []
        self.boundaries: list[float] = []
        self._emb_by_boundary: dict[float, torch.Tensor] = {}
        self._index_of: dict[str, int] = {}
        self._final_emb: torch.Tensor | None = None
        self._dim = 0

    def _row_embedding(self, emb: torch.Tensor, card_key: str) -> np.ndarray:
        idx = self._index_of.get(card_key)
        if idx is None:
            return np.zeros(self._dim, dtype=np.float32)
        return emb[idx].numpy()

    def _slice_boundaries(self, df: pd.DataFrame) -> list[float]:
        ts = df["ts"].to_numpy(dtype=float)
        qs = np.linspace(0.0, 1.0, _N_SLICES + 1)[:-1]
        return sorted({float(np.quantile(ts, q)) for q in qs})

    def _embeddings_at(self, df: pd.DataFrame, as_of: float) -> torch.Tensor:
        torch.manual_seed(self.seed)
        snap = build_snapshot(df, as_of, node_universe=self.node_universe)
        self._index_of = snap.index_of
        return snap.sage_embeddings(self.layers)

    def _feature_matrix(self, df: pd.DataFrame, boundaries: list[float],
                        emb_by_boundary: dict[float, torch.Tensor],
                        final_emb: torch.Tensor) -> np.ndarray:
        feats = np.zeros((len(df), self._dim), dtype=np.float32)
        ts = df["ts"].to_numpy(dtype=float)
        cards = df["cardholder_id"].astype(str).to_numpy()
        for i in range(len(df)):
            b = None
            for cand in boundaries:
                if cand <= ts[i]:
                    b = cand
                else:
                    break
            emb = emb_by_boundary[b] if b is not None else final_emb
            feats[i] = self._row_embedding(emb, _node_key("card", cards[i]))
        return feats

    def fit(self, train_df: pd.DataFrame) -> GraphSAGEModel:
        self._build_universe(train_df)
        self.boundaries = self._slice_boundaries(train_df)
        self._emb_by_boundary = {b: self._embeddings_at(train_df, b) for b in self.boundaries}
        self._final_emb = self._embeddings_at(train_df, float(train_df["ts"].max()) + 1.0)
        self._fit_df_cache = train_df

        mask = mature_mask(train_df)
        tr = train_df[mask]
        X = self._feature_matrix(tr, self.boundaries, self._emb_by_boundary, self._final_emb)
        y = observed_labels(tr)
        if len(np.unique(y)) < 2:
            self._degenerate = True
            self._pos_rate = float(y.mean()) if len(y) else 0.0
        else:
            self._degenerate = False
            self.head.fit(X, y)
        return self

    def _build_universe(self, df: pd.DataFrame) -> None:
        snap: GraphSnapshot = build_snapshot(df, float(df["ts"].max()) + 1.0)
        self.node_universe = snap.node_ids
        self._index_of = snap.index_of
        self._dim = snap.sage_embeddings(self.layers).shape[1]

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        X = self._feature_matrix(df, self.boundaries, self._emb_by_boundary, self._final_emb)
        if getattr(self, "_degenerate", False):
            return np.full(len(df), self._pos_rate, dtype=float)
        return self.head.predict_proba(X)[:, 1]
