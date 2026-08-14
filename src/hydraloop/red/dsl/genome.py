"""The Genome dataclass, canonical serialisation, and content-addressed IDs."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .spec import FAMILIES, GENE_SPEC, SCHEMA_VERSION, default_genes

_FLOAT_ROUND = 10
_SIMPLEX_TOL = 1e-6


class GenomeValidationError(ValueError):
    """Raised when a genome violates the DSL contract."""


def _canonicalise(obj: Any) -> Any:
    """Recursively normalise for hashing: sort keys, round floats.

    Floats are rounded so that arithmetic noise cannot change a genome_id while
    representing the same attack.
    """
    if isinstance(obj, dict):
        return {k: _canonicalise(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        return [_canonicalise(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return round(obj, _FLOAT_ROUND)
    return obj


def canonical_json(obj: Any) -> str:
    return json.dumps(_canonicalise(obj), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Genome:
    family: str
    genes: dict[str, Any]
    attack_id: str | None = None
    parent_id: str | None = None
    schema_version: str = SCHEMA_VERSION
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "family": self.family,
            "attack_id": self.attack_id,
            "parent_id": self.parent_id,
            "genes": self.genes,
        }

    @property
    def genome_id(self) -> str:
        """BLAKE2b over the canonical JSON of the identity-bearing fields.

        ``label`` and ``parent_id`` are excluded so lineage bookkeeping cannot
        change a genome's identity; two genomes with identical genes and family
        share an id regardless of how they were produced.
        """
        identity = {
            "schema_version": self.schema_version,
            "family": self.family,
            "attack_id": self.attack_id,
            "genes": self.genes,
        }
        digest = hashlib.blake2b(canonical_json(identity).encode("utf-8"), digest_size=8)
        return digest.hexdigest()

    def validate(self) -> None:
        validate_genome_dict(self.to_dict())


def genome_from_dict(data: dict[str, Any]) -> Genome:
    validate_genome_dict(data)
    return Genome(
        family=data["family"],
        genes=data["genes"],
        attack_id=data.get("attack_id"),
        parent_id=data.get("parent_id"),
        schema_version=data.get("schema_version", SCHEMA_VERSION),
        label=data.get("label"),
    )


def default_genome(family: str = "social_engineering", attack_id: str | None = None) -> Genome:
    return Genome(family=family, genes=default_genes(), attack_id=attack_id)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def genome_from_template(
    family: str, attack_id: str, template: dict[str, Any] | None = None
) -> Genome:
    """Build a valid genome by merging a scenario's partial template over defaults."""
    genes = _deep_merge(default_genes(), template or {})
    g = Genome(family=family, genes=genes, attack_id=attack_id, label=f"{attack_id}.g0.v0")
    g.validate()
    return g


def _check_field(path: str, spec, value: Any) -> None:
    kind = spec.kind
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GenomeValidationError(f"{path}: expected float, got {type(value).__name__}")
        if not (spec.lo <= float(value) <= spec.hi):
            raise GenomeValidationError(f"{path}: {value} out of range [{spec.lo}, {spec.hi}]")
    elif kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise GenomeValidationError(f"{path}: expected int, got {type(value).__name__}")
        if not (spec.lo <= value <= spec.hi):
            raise GenomeValidationError(f"{path}: {value} out of range [{spec.lo}, {spec.hi}]")
    elif kind == "bool":
        if not isinstance(value, bool):
            raise GenomeValidationError(f"{path}: expected bool")
    elif kind == "categorical":
        if value not in spec.options:
            raise GenomeValidationError(f"{path}: '{value}' not in {spec.options}")
    elif kind == "simplex":
        if not isinstance(value, dict) or set(value) != set(spec.members):
            raise GenomeValidationError(f"{path}: simplex must have members {spec.members}")
        for m, w in value.items():
            if isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0:
                raise GenomeValidationError(f"{path}.{m}: weight must be non-negative number")
        total = sum(value.values())
        if abs(total - 1.0) > _SIMPLEX_TOL:
            raise GenomeValidationError(f"{path}: weights must sum to 1.0 (got {total})")
    elif kind == "fraction_ladder":
        if not isinstance(value, list) or not value:
            raise GenomeValidationError(f"{path}: expected non-empty list")
        if spec.min_len and len(value) < spec.min_len:
            raise GenomeValidationError(f"{path}: needs >= {spec.min_len} steps")
        if spec.max_len and len(value) > spec.max_len:
            raise GenomeValidationError(f"{path}: needs <= {spec.max_len} steps")
        prev = -1.0
        for i, v in enumerate(value):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise GenomeValidationError(f"{path}[{i}]: expected number")
            if not (spec.lo <= float(v) <= spec.hi):
                raise GenomeValidationError(f"{path}[{i}]: {v} out of range")
            if float(v) < prev:
                raise GenomeValidationError(f"{path}: ladder must be non-decreasing")
            prev = float(v)
    else:  # pragma: no cover - guards against an unhandled spec kind
        raise GenomeValidationError(f"{path}: unknown gene kind '{kind}'")


def validate_genome_dict(data: dict[str, Any]) -> None:
    if data.get("family") not in FAMILIES:
        raise GenomeValidationError(f"family '{data.get('family')}' not in {FAMILIES}")
    genes = data.get("genes")
    if not isinstance(genes, dict):
        raise GenomeValidationError("genes must be an object")

    unknown_groups = set(genes) - set(GENE_SPEC)
    if unknown_groups:
        raise GenomeValidationError(f"unknown gene groups: {sorted(unknown_groups)}")

    for group, fields in GENE_SPEC.items():
        if group not in genes:
            raise GenomeValidationError(f"missing gene group '{group}'")
        block = genes[group]
        if not isinstance(block, dict):
            raise GenomeValidationError(f"{group}: must be an object")
        unknown_fields = set(block) - set(fields)
        if unknown_fields:
            raise GenomeValidationError(f"{group}: unknown genes {sorted(unknown_fields)}")
        for name, spec in fields.items():
            if name not in block:
                raise GenomeValidationError(f"{group}.{name}: missing")
            _check_field(f"{group}.{name}", spec, block[name])

    vs = genes["victim_selection"]
    if vs["balance_percentile_lo"] > vs["balance_percentile_hi"]:
        raise GenomeValidationError("victim_selection: balance_percentile_lo > hi")


__all__ = [
    "Genome",
    "GenomeValidationError",
    "canonical_json",
    "genome_from_dict",
    "genome_from_template",
    "default_genome",
    "validate_genome_dict",
]
