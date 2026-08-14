"""The dedicated point-in-time leakage test for the graph snapshot.

An edge that appears at or after ``as_of`` must never enter the aggregation.
This is the single most common leakage trap in graph fraud models, so it gets
its own explicit test.
"""

from __future__ import annotations

import pandas as pd

from hydraloop.blue.graph.snapshot import build_snapshot


def _df():
    return pd.DataFrame(
        [
            {"ts": 10.0, "cardholder_id": "C1", "device_id": "D1", "merchant_id": "M1", "payee_id": None},
            {"ts": 50.0, "cardholder_id": "C1", "device_id": "D2", "merchant_id": "M1", "payee_id": None},
            {"ts": 100.0, "cardholder_id": "C1", "device_id": "D3", "merchant_id": "M2", "payee_id": None},
        ]
    )


def test_future_edges_excluded():
    df = _df()
    snap = build_snapshot(df, as_of=50.0)
    # Only the ts=10 transaction is strictly before as_of=50.
    # Undirected storage means one transaction (card-device, card-merchant) -> 4 directed entries.
    assert snap.edge_index.shape[1] == 4


def test_edge_at_exactly_as_of_is_excluded():
    df = _df()
    snap = build_snapshot(df, as_of=50.0)
    idx_d2 = snap.index_of["device:D2"]
    deg = snap.base_features()[idx_d2, -1].item()
    assert deg == 0.0  # the ts=50 edge is not counted at as_of=50


def test_embedding_changes_only_with_past_edges():
    df = _df()
    universe = build_snapshot(df, as_of=1e9).node_ids
    early = build_snapshot(df, as_of=20.0, node_universe=universe).sage_embeddings()
    late = build_snapshot(df, as_of=200.0, node_universe=universe).sage_embeddings()
    card = build_snapshot(df, as_of=1e9, node_universe=universe).index_of["card:C1"]
    # More history strictly before as_of changes the card's embedding.
    assert not (early[card] == late[card]).all()
