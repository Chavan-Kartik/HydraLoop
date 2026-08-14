"""Validate the threat catalog and keep the genome JSON Schema in sync.

CI runs this. It fails if:
  - the committed genome schema drifts from the executable gene specification;
  - any catalog attack file is missing required fields or references an
    unknown family or invalid enum value.
"""

from __future__ import annotations

import json
import sys

import yaml

from hydraloop.paths import ATTACKS_DIR, CATALOG_DIR
from hydraloop.red.dsl.schema_export import build_json_schema
from hydraloop.red.dsl.spec import FAMILIES

REQUIRED_ATTACK_FIELDS = [
    "attack_id",
    "attack_name",
    "family",
    "abstraction_level",
    "assumptions",
    "behavioral_signals",
    "detection_hypotheses",
    "mitigation_options",
    "validation_status",
    "harm_review",
    "risk_level",
]

VALID_VALIDATION_STATUS = {
    "unverified_hypothetical",
    "assumed",
    "reference_supported",
}


def check_genome_schema() -> list[str]:
    path = CATALOG_DIR / "genome.schema.json"
    if not path.exists():
        return [f"missing {path}"]
    committed = json.loads(path.read_text(encoding="utf-8"))
    if committed != build_json_schema():
        return ["genome.schema.json is stale; regenerate with schema_export.write_schema"]
    return []


def check_catalog() -> list[str]:
    problems: list[str] = []
    if not ATTACKS_DIR.exists():
        return problems
    files = sorted(ATTACKS_DIR.glob("*.yaml"))
    seen_ids: set[str] = set()
    family_counts: dict[str, int] = {f: 0 for f in FAMILIES}
    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for field_name in REQUIRED_ATTACK_FIELDS:
            if field_name not in data:
                problems.append(f"{f.name}: missing '{field_name}'")
        fam = data.get("family")
        if fam not in FAMILIES:
            problems.append(f"{f.name}: family '{fam}' not in {FAMILIES}")
        else:
            family_counts[fam] += 1
        aid = data.get("attack_id")
        if aid in seen_ids:
            problems.append(f"{f.name}: duplicate attack_id '{aid}'")
        seen_ids.add(aid)
        vs = data.get("validation_status")
        if vs not in VALID_VALIDATION_STATUS:
            problems.append(f"{f.name}: validation_status '{vs}' invalid")
        hr = data.get("harm_review")
        if not isinstance(hr, str) or not hr.strip():
            problems.append(f"{f.name}: harm_review must be a non-empty string")
    if files:
        empty = [fam for fam, c in family_counts.items() if c == 0]
        if empty:
            problems.append(f"families with no scenarios: {empty}")
    return problems


def main() -> int:
    problems = check_genome_schema() + check_catalog()
    if problems:
        print("Catalog validation FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Catalog validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
