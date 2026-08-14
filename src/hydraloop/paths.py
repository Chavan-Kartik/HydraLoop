"""Canonical filesystem locations, resolved relative to the repository root.

Everything writes under ``reports/runs/<run_id>/`` or ``data/`` so that a demo
never depends on a network service being reachable.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIGS_DIR = REPO_ROOT / "configs"
CATALOG_DIR = REPO_ROOT / "catalog"
ATTACKS_DIR = CATALOG_DIR / "attacks"
DATA_DIR = REPO_ROOT / "data"
HOLDOUT_DIR = DATA_DIR / "holdout_zeroday"
REPORTS_DIR = REPO_ROOT / "reports"
RUNS_DIR = REPORTS_DIR / "runs"
EXAMPLES_DIR = REPORTS_DIR / "examples"


def run_dir(run_id: str) -> Path:
    """Directory for a single run's artefacts, created on demand."""
    d = RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, RUNS_DIR, EXAMPLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
