"""Aggregate the latest run's artefacts into a single index for the deck."""

from __future__ import annotations

import json
from pathlib import Path

from hydraloop.paths import RUNS_DIR


def latest_run() -> Path | None:
    if not RUNS_DIR.exists():
        return None
    runs = sorted((p for p in RUNS_DIR.iterdir() if p.is_dir()), key=lambda p: p.name)
    return runs[-1] if runs else None


def main() -> int:
    run = latest_run()
    if run is None:
        print("No runs found under reports/runs/. Run `python -m hydraloop demo` first.")
        return 1
    artefacts = sorted(p.name for p in run.iterdir() if p.is_file())
    index = {"run_id": run.name, "artefacts": artefacts}
    (run / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Indexed {len(artefacts)} artefacts for {run.name}")
    for a in artefacts:
        print(f"  - {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
