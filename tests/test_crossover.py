import numpy as np
import pytest

from hydraloop.red.dsl import crossover, default_genome
from hydraloop.red.dsl.crossover import CrossoverError


def test_cross_family_rejected():
    gen = np.random.default_rng(0)
    a = default_genome(family="social_engineering")
    b = default_genome(family="card_testing")
    with pytest.raises(CrossoverError):
        crossover(a, b, gen)


def test_same_family_crossover_valid():
    gen = np.random.default_rng(1)
    a = default_genome(family="money_movement")
    b = default_genome(family="money_movement")
    b.genes["network_topology"]["mule_fanout"] = 9
    child = crossover(a, b, gen)
    child.validate()
    assert child.family == "money_movement"


def test_child_records_parent():
    gen = np.random.default_rng(2)
    a = default_genome(family="account_takeover", attack_id="AF-05")
    b = default_genome(family="account_takeover")
    child = crossover(a, b, gen)
    assert child.parent_id == a.genome_id
