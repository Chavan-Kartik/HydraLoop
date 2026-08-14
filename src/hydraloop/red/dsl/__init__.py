"""Attack Genome DSL: the constrained parameter space the Red Team searches.

The gene specification in :mod:`spec` is the single source of truth. The JSON
Schema mirror and every validator are derived from it, so the executable code
and the published contract can never silently drift apart.
"""

from .genome import Genome, canonical_json, genome_from_dict
from .spec import FAMILIES, GENE_SPEC, SCHEMA_VERSION

__all__ = [
    "Genome",
    "canonical_json",
    "genome_from_dict",
    "FAMILIES",
    "GENE_SPEC",
    "SCHEMA_VERSION",
]
