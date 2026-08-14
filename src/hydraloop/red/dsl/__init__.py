"""Attack Genome DSL: the constrained parameter space the Red Team searches.

The gene specification in :mod:`spec` is the single source of truth. The JSON
Schema mirror and every validator are derived from it, so the executable code
and the published contract can never silently drift apart.
"""

from .crossover import CrossoverError, crossover
from .genome import (
    Genome,
    canonical_json,
    default_genome,
    genome_from_dict,
    genome_from_template,
)
from .mutate import mutate
from .render import render_brief
from .spec import FAMILIES, GENE_SPEC, SCHEMA_VERSION

__all__ = [
    "Genome",
    "canonical_json",
    "genome_from_dict",
    "genome_from_template",
    "default_genome",
    "mutate",
    "crossover",
    "CrossoverError",
    "render_brief",
    "FAMILIES",
    "GENE_SPEC",
    "SCHEMA_VERSION",
]
