"""Populate the demo example run and freeze offline seed JSON for the UI.

Run this after changing the command-center projections so the venue-offline
fallback under ``ui/public/seed`` matches what the live API returns.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from hydraloop.api import ledger_source as src
from hydraloop.catalog import load_catalog
from hydraloop.paths import EXAMPLES_DIR, REPO_ROOT, RUNS_DIR
from hydraloop.red.dsl.genome import genome_from_template
from hydraloop.red.dsl.render import render_brief

DEMO_RUN = "example_coevolution"
SEED_DIR = REPO_ROOT / "ui" / "public" / "seed"


def _ensure_genomes(run_path: Path) -> None:
    manifest = [
        {
            "attack_id": s.attack_id,
            "genome_id": genome_from_template(s.family, s.attack_id, s.genome_template).genome_id,
            "family": s.family,
            "brief": render_brief(genome_from_template(s.family, s.attack_id, s.genome_template)),
        }
        for s in load_catalog()
        if s.evolvable
    ]
    (run_path / "genomes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _ensure_investigations(run_path: Path) -> None:
    if (run_path / "investigations.json").exists():
        return
    donor = RUNS_DIR / "run_blue_test" / "investigations.json"
    if donor.exists():
        shutil.copy(donor, run_path / "investigations.json")


def main() -> None:
    run_path = EXAMPLES_DIR / DEMO_RUN
    _ensure_genomes(run_path)
    _ensure_investigations(run_path)

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        "runs.json": {"runs": src.list_runs()},
        "arena.json": {"run_id": DEMO_RUN, "events": src.arena_events(DEMO_RUN)},
        "scoreboard.json": src.scoreboard_series(DEMO_RUN),
        "threats.json": src.threat_catalog(),
        "lineage.json": src.genome_lineage(DEMO_RUN),
        "investigations.json": src.investigations(DEMO_RUN),
        "governance.json": src.verify_ledger(DEMO_RUN),
        "kpis.json": src.kpis(DEMO_RUN),
        "strategist.json": src.strategist(DEMO_RUN),
    }
    for name, payload in payloads.items():
        (SEED_DIR / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {name}")


if __name__ == "__main__":
    main()
