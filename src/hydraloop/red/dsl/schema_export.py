"""Derive a JSON Schema for genomes from the executable gene specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .spec import FAMILIES, GENE_SPEC, SCHEMA_VERSION


def _field_schema(spec) -> dict[str, Any]:
    if spec.kind == "float":
        return {"type": "number", "minimum": spec.lo, "maximum": spec.hi}
    if spec.kind == "int":
        return {"type": "integer", "minimum": spec.lo, "maximum": spec.hi}
    if spec.kind == "bool":
        return {"type": "boolean"}
    if spec.kind == "categorical":
        return {"type": "string", "enum": list(spec.options)}
    if spec.kind == "simplex":
        return {
            "type": "object",
            "properties": {m: {"type": "number", "minimum": 0} for m in spec.members},
            "required": list(spec.members),
            "additionalProperties": False,
        }
    if spec.kind == "fraction_ladder":
        return {
            "type": "array",
            "items": {"type": "number", "minimum": spec.lo, "maximum": spec.hi},
            "minItems": spec.min_len or 1,
            "maxItems": spec.max_len or 6,
        }
    raise ValueError(f"unknown gene kind {spec.kind}")


def build_json_schema() -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for group, fields in GENE_SPEC.items():
        groups[group] = {
            "type": "object",
            "properties": {name: _field_schema(spec) for name, spec in fields.items()},
            "required": list(fields),
            "additionalProperties": False,
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "HydraLoop Attack Genome",
        "type": "object",
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "family": {"type": "string", "enum": list(FAMILIES)},
            "attack_id": {"type": ["string", "null"]},
            "parent_id": {"type": ["string", "null"]},
            "genes": {
                "type": "object",
                "properties": groups,
                "required": list(GENE_SPEC),
                "additionalProperties": False,
            },
        },
        "required": ["family", "genes"],
        "additionalProperties": True,
    }


def write_schema(path: Path) -> Path:
    path.write_text(json.dumps(build_json_schema(), indent=2), encoding="utf-8")
    return path
