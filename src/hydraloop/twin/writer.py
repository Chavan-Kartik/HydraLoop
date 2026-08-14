"""Persist twin output and compute a deterministic content digest.

The golden-run digest hashes a canonical JSONL projection of the transactions,
not the Parquet bytes: Parquet embeds writer version and creation metadata that
change between environments and would make a byte-level comparison flap.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

_DIGEST_COLUMNS = [
    "txn_id",
    "ts",
    "cardholder_id",
    "merchant_id",
    "channel",
    "amount_minor",
    "action",
    "approved",
    "captured_minor",
    "is_fraud",
    "disputed",
]


def _canonical_rows(transactions: list[dict]) -> list[str]:
    rows = sorted(transactions, key=lambda t: (t["ts"], t["txn_id"]))
    lines = []
    for t in rows:
        proj = {}
        for c in _DIGEST_COLUMNS:
            v = t.get(c)
            if isinstance(v, float):
                v = round(v, 6)
            proj[c] = v
        lines.append(json.dumps(proj, sort_keys=True, separators=(",", ":")))
    return lines


def canonical_digest(transactions: list[dict]) -> str:
    h = hashlib.blake2b(digest_size=16)
    for line in _canonical_rows(transactions):
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def write_dataset(
    out_dir: Path,
    events: list[dict],
    transactions: list[dict],
    tag: str = "legit",
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_df = pd.DataFrame(events)
    tx_df = pd.DataFrame(transactions)

    ev_path = out_dir / f"events_{tag}.parquet"
    tx_path = out_dir / f"transactions_{tag}.parquet"
    ev_df.to_parquet(ev_path, index=False)
    tx_df.to_parquet(tx_path, index=False)

    digest = canonical_digest(transactions)
    meta = {
        "synthetic": True,
        "tag": tag,
        "n_events": len(events),
        "n_transactions": len(transactions),
        "canonical_digest": digest,
    }
    meta_path = out_dir / f"dataset_{tag}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"events": ev_path, "transactions": tx_path, "meta": meta_path}
