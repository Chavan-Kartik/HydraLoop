"""Tokenise each entity's recent history into a padded sequence.

A row's sequence is built only from that cardholder's *prior* transactions, so
it is point-in-time correct by construction: the current transaction is appended
to the running history only after its own sequence has been emitted.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

TOKEN_DIM = 6
_D30 = 30 * 86400.0


def _token(row, prev_ts: float | None) -> list[float]:
    amount_log = math.log1p(max(0.0, float(row["amount_minor"])))
    channel = float(row.get("channel_code", 0.0))
    gap = 0.0 if prev_ts is None else math.log1p(max(0.0, float(row["ts"]) - prev_ts))
    hour = (float(row["ts"]) / 3600.0) % 24.0
    return [
        amount_log / 15.0,
        channel / 2.0,
        gap / 15.0,
        hour / 24.0,
        float(row.get("device_is_new", 0.0)),
        float(row.get("payee_is_new", 0.0)),
    ]


def build_sequences(df: pd.DataFrame, max_len: int = 16) -> tuple[np.ndarray, np.ndarray]:
    """Return (padded tensor [n, max_len, TOKEN_DIM], lengths [n])."""
    order = df["ts"].to_numpy(dtype=float).argsort(kind="stable")
    inv = np.empty_like(order)
    inv[order] = np.arange(len(order))

    histories: dict[str, list[list[float]]] = {}
    last_ts: dict[str, float] = {}
    seqs: list[np.ndarray] = [None] * len(df)  # type: ignore[list-item]
    lengths = np.zeros(len(df), dtype=np.int64)

    rows = df.iloc[order]
    for pos, (_, row) in enumerate(rows.iterrows()):
        cid = str(row["cardholder_id"])
        hist = histories.get(cid, [])
        window = hist[-max_len:]
        arr = np.zeros((max_len, TOKEN_DIM), dtype=np.float32)
        if window:
            arr[max_len - len(window):] = np.array(window, dtype=np.float32)
        original_index = order[pos]
        seqs[original_index] = arr
        lengths[original_index] = len(window)
        hist.append(_token(row, last_ts.get(cid)))
        histories[cid] = hist
        last_ts[cid] = float(row["ts"])

    return np.stack(seqs), lengths
