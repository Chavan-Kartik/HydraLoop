"""Append-only, hash-chained generation ledger.

Each entry embeds the previous entry's digest, so any edit to history is
detectable on load. This makes the Governance screen's tamper-evidence claim
concrete rather than rhetorical.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS = "0" * 32


def _digest(prev_hash: str, payload: dict[str, Any]) -> str:
    body = prev_hash + json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


class GenerationLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = []

    @property
    def head_hash(self) -> str:
        return self.entries[-1]["entry_hash"] if self.entries else GENESIS

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        prev = self.head_hash
        entry_hash = _digest(prev, payload)
        entry = {"prev_hash": prev, "payload": payload, "entry_hash": entry_hash}
        self.entries.append(entry)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    @staticmethod
    def load(path: Path) -> GenerationLedger:
        ledger = GenerationLedger(path)
        if not path.exists():
            return ledger
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ledger.entries.append(json.loads(line))
        ledger.verify()
        return ledger

    def verify(self) -> None:
        prev = GENESIS
        for i, entry in enumerate(self.entries):
            if entry["prev_hash"] != prev:
                raise ValueError(f"ledger break at entry {i}: prev_hash mismatch")
            expected = _digest(entry["prev_hash"], entry["payload"])
            if entry["entry_hash"] != expected:
                raise ValueError(f"ledger tamper at entry {i}: entry_hash mismatch")
            prev = entry["entry_hash"]
