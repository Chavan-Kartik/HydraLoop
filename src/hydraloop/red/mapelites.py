"""MAP-Elites quality-diversity search over the attack genome space.

Five behavioural descriptors bin the space into exactly
4 x 3 x 3 x 3 x 2 = 216 cells, so archive coverage is a clean percentage. The
archive keeps the fittest genome discovered per cell; search proceeds by mutating
random elites. Coverage and mean novelty distance are reported each generation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .dsl.genome import Genome
from .dsl.mutate import mutate

# (descriptor name, number of bins). Product is 216 by construction.
DESCRIPTORS = (
    ("velocity", 4),
    ("amount_profile", 3),
    ("fan_out", 3),
    ("dwell", 3),
    ("target_side", 2),
)
TOTAL_CELLS = 4 * 3 * 3 * 3 * 2


def _bin(value: float, edges: list[float]) -> int:
    for i, e in enumerate(edges):
        if value < e:
            return i
    return len(edges)


def descriptor(genome: Genome) -> tuple[int, int, int, int, int]:
    g = genome.genes
    # Velocity: shorter inter-transaction delay means higher velocity.
    mu = g["timing_policy"]["inter_txn_delay_mu"]
    velocity = 3 - _bin(mu, [3.0, 6.0, 9.0])
    amount = _bin(g["amount_policy"]["max_fraction"], [0.34, 0.67])
    fan_out = _bin(g["network_topology"]["mule_fanout"], [3, 8])
    dwell = _bin(g["timing_policy"]["dwell_before_cashout_h"], [12.0, 48.0])
    target = 0 if g["victim_selection"]["target_side"] == "victim" else 1
    return (velocity, amount, fan_out, dwell, target)


def cell_index(desc: tuple[int, ...]) -> int:
    idx = 0
    for (_name, bins), d in zip(DESCRIPTORS, desc, strict=True):
        idx = idx * bins + d
    return idx


@dataclass
class Elite:
    genome: Genome
    fitness: float
    descriptor: tuple[int, ...]


class MapElitesArchive:
    def __init__(self) -> None:
        self.cells: dict[int, Elite] = {}

    def add(self, genome: Genome, fit: float) -> bool:
        desc = descriptor(genome)
        key = cell_index(desc)
        current = self.cells.get(key)
        if current is None or fit > current.fitness:
            self.cells[key] = Elite(genome, fit, desc)
            return True
        return False

    @property
    def coverage(self) -> float:
        return len(self.cells) / TOTAL_CELLS

    def best(self) -> Elite | None:
        if not self.cells:
            return None
        return max(self.cells.values(), key=lambda e: e.fitness)

    def mean_novelty(self) -> float:
        """Mean nearest-neighbour Hamming distance between occupied descriptors."""
        descs = [np.array(e.descriptor) for e in self.cells.values()]
        if len(descs) < 2:
            return 0.0
        dists = []
        for i, a in enumerate(descs):
            others = [np.sum(a != b) for j, b in enumerate(descs) if j != i]
            dists.append(min(others))
        return float(np.mean(dists))


def run_map_elites(
    seeds: list[Genome],
    evaluate: Callable[[Genome], float],
    iterations: int,
    rng: np.random.Generator,
    mutation_rate: float = 0.3,
    archive: MapElitesArchive | None = None,
) -> MapElitesArchive:
    # Passing an existing archive lets coverage accumulate across generations.
    archive = archive if archive is not None else MapElitesArchive()
    for g in seeds:
        archive.add(g, evaluate(g))
    for _ in range(iterations):
        if not archive.cells:
            break
        parent = rng.choice(list(archive.cells.values()))
        child = mutate(parent.genome, rng, mutation_rate)
        archive.add(child, evaluate(child))
    return archive
