"""Run manifest: the reproducibility record written for every run."""

from __future__ import annotations

import importlib.metadata as md
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .config import Config

_TRACKED_PACKAGES = (
    "numpy",
    "pandas",
    "scipy",
    "scikit-learn",
    "lightgbm",
    "torch",
    "duckdb",
    "pyarrow",
)


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "unknown"


def _package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = "not-installed"
    return out


def write_manifest(run_dir: Path, config: Config, run_id: str) -> Path:
    manifest = {
        "project": "HydraLoop",
        "run_id": run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "config_path": str(config.source_path) if config.source_path else None,
        "config_hash": config.config_hash,
        "seed": config.simulation.seed,
        "package_versions": _package_versions(),
        "safety": {
            "synthetic_only": True,
            "live_targeting": False,
            "content_generation": False,
            "operational_tooling": False,
        },
    }
    out = run_dir / "run_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out
