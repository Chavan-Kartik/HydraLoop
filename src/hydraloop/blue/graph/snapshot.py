"""A point-in-time graph over card / device / merchant / payee nodes.

The single leakage trap in graph fraud models is aggregating over edges that did
not exist yet at decision time. A snapshot is built with a hard ``as_of`` filter
(``edge_ts < as_of``), so an edge from the future cannot enter the aggregation.
The dedicated leakage test asserts exactly this.

Aggregation is mean-pool GraphSAGE, hand-rolled with ``torch.index_add_`` rather
than pulled from ``torch-geometric`` -- fewer moving parts and nothing to install
that breaks on Windows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch

_NODE_TYPES = ("card", "device", "merchant", "payee")
_TYPE_INDEX = {t: i for i, t in enumerate(_NODE_TYPES)}


def _node_key(kind: str, value: str) -> str:
    return f"{kind}:{value}"


@dataclass
class GraphSnapshot:
    node_ids: list[str]
    node_type: np.ndarray  # int code per node
    edge_index: torch.Tensor  # (2, E) undirected pairs, both directions stored
    index_of: dict[str, int]

    @property
    def num_nodes(self) -> int:
        return len(self.node_ids)

    def base_features(self) -> torch.Tensor:
        """Static node features: one-hot type plus log-degree in this snapshot."""
        n = self.num_nodes
        onehot = torch.zeros((n, len(_NODE_TYPES)), dtype=torch.float32)
        onehot[torch.arange(n), torch.from_numpy(self.node_type)] = 1.0
        deg = torch.zeros((n, 1), dtype=torch.float32)
        if self.edge_index.numel():
            src = self.edge_index[0]
            deg.index_add_(0, src, torch.ones((src.shape[0], 1), dtype=torch.float32))
        return torch.cat([onehot, torch.log1p(deg)], dim=1)

    def mean_aggregate(self, x: torch.Tensor) -> torch.Tensor:
        """One GraphSAGE mean-pool step: each node averages its neighbours' x."""
        n = self.num_nodes
        agg = torch.zeros_like(x)
        if self.edge_index.numel() == 0:
            return agg
        src, dst = self.edge_index[0], self.edge_index[1]
        agg.index_add_(0, dst, x[src])
        deg = torch.zeros((n, 1), dtype=torch.float32)
        deg.index_add_(0, dst, torch.ones((dst.shape[0], 1), dtype=torch.float32))
        return agg / deg.clamp_min(1.0)

    def sage_embeddings(self, layers: int = 2) -> torch.Tensor:
        """Concatenate the base features with ``layers`` rounds of mean-pooling."""
        x = self.base_features()
        outputs = [x]
        h = x
        for _ in range(layers):
            h = self.mean_aggregate(h)
            outputs.append(h)
        return torch.cat(outputs, dim=1)


def build_snapshot(df: pd.DataFrame, as_of: float, node_universe: list[str] | None = None) -> GraphSnapshot:
    """Build the graph from transactions strictly before ``as_of``.

    ``node_universe`` fixes the node index across snapshots so that embeddings
    are comparable over time; nodes with no edges yet simply have degree zero.
    """
    past = df[df["ts"] < as_of]

    def edges_from(row) -> list[tuple[str, str]]:
        card = _node_key("card", str(row["cardholder_id"]))
        out = [(card, _node_key("device", str(row["device_id"]))),
               (card, _node_key("merchant", str(row["merchant_id"])))]
        payee = row.get("payee_id")
        if payee is not None and not (isinstance(payee, float) and np.isnan(payee)):
            out.append((card, _node_key("payee", str(payee))))
        return out

    if node_universe is None:
        keys: set[str] = set()
        for _, row in df.iterrows():
            for a, b in edges_from(row):
                keys.add(a)
                keys.add(b)
        node_universe = sorted(keys)

    index_of = {k: i for i, k in enumerate(node_universe)}
    node_type = np.array(
        [_TYPE_INDEX[k.split(":", 1)[0]] for k in node_universe], dtype=np.int64
    )

    src: list[int] = []
    dst: list[int] = []
    for _, row in past.iterrows():
        for a, b in edges_from(row):
            ia, ib = index_of.get(a), index_of.get(b)
            if ia is None or ib is None:
                continue
            src.extend([ia, ib])  # store both directions for undirected mean-pool
            dst.extend([ib, ia])
    edge_index = torch.tensor([src, dst], dtype=torch.long) if src else torch.zeros((2, 0), dtype=torch.long)
    return GraphSnapshot(node_universe, node_type, edge_index, index_of)
