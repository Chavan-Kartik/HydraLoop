"""Load and validate threat-catalog scenarios against the JSON Schema."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ..paths import ATTACKS_DIR, CATALOG_DIR


@dataclass(frozen=True)
class ThreatScenario:
    attack_id: str
    attack_name: str
    family: str
    evolvable: bool
    genome_template: dict[str, Any]
    raw: dict[str, Any]


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads((CATALOG_DIR / "schema.json").read_text(encoding="utf-8"))


def _validate(data: dict[str, Any], source: str) -> None:
    try:
        jsonschema.validate(data, _schema())
    except jsonschema.ValidationError as exc:
        raise ValueError(f"{source}: {exc.message}") from exc


def load_scenario(path: Path) -> ThreatScenario:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _validate(data, path.name)
    return ThreatScenario(
        attack_id=data["attack_id"],
        attack_name=data["attack_name"],
        family=data["family"],
        evolvable=bool(data.get("evolvable", False)),
        genome_template=data.get("genome_template", {}),
        raw=data,
    )


def load_catalog(directory: Path | None = None) -> list[ThreatScenario]:
    directory = directory or ATTACKS_DIR
    scenarios = [load_scenario(p) for p in sorted(directory.glob("*.yaml"))]
    ids = [s.attack_id for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate attack_id in catalog")
    return scenarios
