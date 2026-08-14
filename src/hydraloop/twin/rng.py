"""Deterministic random-number streams.

Each agent draws from its own child stream derived from the root seed. Using
one stream per agent (rather than a single global stream) keeps a run
reproducible even if agents are later processed in parallel or in a different
order, because an agent's draws no longer depend on how many draws other agents
made before it.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _stable_key(name: str) -> int:
    digest = hashlib.blake2b(name.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


class RngRegistry:
    def __init__(self, root_seed: int) -> None:
        self.root_seed = int(root_seed)
        self._cache: dict[str, np.random.Generator] = {}

    def stream(self, name: str) -> np.random.Generator:
        """Return the generator for a named agent or subsystem, cached."""
        gen = self._cache.get(name)
        if gen is None:
            seq = np.random.SeedSequence([self.root_seed, _stable_key(name)])
            gen = np.random.default_rng(seq)
            self._cache[name] = gen
        return gen
