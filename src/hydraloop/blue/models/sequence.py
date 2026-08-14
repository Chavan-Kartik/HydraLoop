"""A GRU over tokenised 30-day history.

Aggregate tabular features miss ordering; a burst of small probes followed by a
large transfer looks different in sequence than the same events shuffled. The
GRU reads the ordered token stream and emits a fraud probability.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import nn

from ..features import mature_mask, observed_labels
from ..sequences import TOKEN_DIM, build_sequences


class _GRUNet(nn.Module):
    def __init__(self, hidden: int = 16) -> None:
        super().__init__()
        self.gru = nn.GRU(TOKEN_DIM, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, h = self.gru(x)
        return self.head(h[-1]).squeeze(-1)


class SequenceModel:
    def __init__(self, seed: int = 42, epochs: int = 12, max_len: int = 16) -> None:
        self.seed = seed
        self.epochs = epochs
        self.max_len = max_len
        self.net = _GRUNet()

    def fit(self, train_df: pd.DataFrame) -> SequenceModel:
        torch.manual_seed(self.seed)
        self.net = _GRUNet()
        mask = mature_mask(train_df)
        tr = train_df[mask]
        seqs, _ = build_sequences(tr, self.max_len)
        y = observed_labels(tr).astype(np.float32)
        if len(np.unique(y)) < 2:
            self._degenerate = True
            self._pos_rate = float(y.mean()) if len(y) else 0.0
            return self
        self._degenerate = False

        X = torch.from_numpy(seqs)
        yt = torch.from_numpy(y)
        pos_weight = torch.tensor([(len(y) - y.sum()) / max(1.0, y.sum())])
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        opt = torch.optim.Adam(self.net.parameters(), lr=0.01)
        self.net.train()
        for _ in range(self.epochs):
            opt.zero_grad()
            logits = self.net(X)
            loss = loss_fn(logits, yt)
            loss.backward()
            opt.step()
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if getattr(self, "_degenerate", False):
            return np.full(len(df), self._pos_rate, dtype=float)
        seqs, _ = build_sequences(df, self.max_len)
        self.net.eval()
        with torch.no_grad():
            logits = self.net(torch.from_numpy(seqs))
            return torch.sigmoid(logits).numpy()
