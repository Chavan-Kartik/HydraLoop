import numpy as np

from hydraloop.red.dsl import default_genome, mutate
from hydraloop.red.dsl.spec import GENE_SPEC


def test_mutation_stays_valid():
    gen = np.random.default_rng(0)
    g = default_genome()
    for _ in range(50):
        g = mutate(g, gen, rate=0.5)
        g.validate()


def test_mutation_clamped():
    gen = np.random.default_rng(1)
    g = default_genome()
    for _ in range(200):
        g = mutate(g, gen, rate=1.0)
    fo = g.genes["network_topology"]["mule_fanout"]
    spec = GENE_SPEC["network_topology"]["mule_fanout"]
    assert spec.lo <= fo <= spec.hi


def test_mutation_sets_parent():
    gen = np.random.default_rng(2)
    g = default_genome(attack_id="AF-09")
    child = mutate(g, gen, rate=1.0)
    assert child.parent_id == g.genome_id


def test_mutation_changes_something():
    gen = np.random.default_rng(3)
    g = default_genome()
    child = mutate(g, gen, rate=1.0)
    assert child.genome_id != g.genome_id
