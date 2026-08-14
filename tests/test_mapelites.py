import numpy as np

from hydraloop.red.dsl.genome import default_genome
from hydraloop.red.mapelites import (
    TOTAL_CELLS,
    cell_index,
    descriptor,
    run_map_elites,
)


def test_exactly_216_cells():
    assert TOTAL_CELLS == 216


def test_descriptor_and_cell_index_in_range():
    g = default_genome()
    desc = descriptor(g)
    assert len(desc) == 5
    idx = cell_index(desc)
    assert 0 <= idx < TOTAL_CELLS


def test_search_expands_coverage():
    rng = np.random.default_rng(0)

    def evaluate(genome):
        # Reward the fan-out gene so search has a gradient to climb.
        return float(genome.genes["network_topology"]["mule_fanout"])

    seeds = [default_genome()]
    archive = run_map_elites(seeds, evaluate, iterations=200, rng=rng)
    assert len(archive.cells) > 1  # more than the single seed cell
    assert 0.0 < archive.coverage <= 1.0
    assert archive.mean_novelty() >= 0.0
    assert archive.best().fitness >= evaluate(seeds[0])
