"""Group-level uniform crossover between two genomes of the same family.

Cross-family crossover is rejected: mixing, say, a card-testing timing policy
into a social-engineering genome produces something that does not correspond to
any coherent attack, so the operator refuses rather than emit nonsense.
"""

from __future__ import annotations

import copy

import numpy as np

from .genome import Genome
from .spec import GENE_SPEC


class CrossoverError(ValueError):
    pass


def crossover(a: Genome, b: Genome, gen: np.random.Generator) -> Genome:
    if a.family != b.family:
        raise CrossoverError(f"cannot cross families {a.family!r} and {b.family!r}")
    genes: dict = {}
    for group in GENE_SPEC:
        source = a if gen.random() < 0.5 else b
        genes[group] = copy.deepcopy(source.genes[group])
    child = Genome(
        family=a.family,
        genes=genes,
        attack_id=a.attack_id,
        parent_id=a.genome_id,
    )
    child.validate()
    return child
