"""Typed configuration loading with deterministic hashing.

The config hash feeds ``run_manifest.json`` so that a run's artefacts can be
traced back to the exact configuration that produced them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .paths import CONFIGS_DIR


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 42
    generations: int = 3
    legitimate_transactions_per_generation: int = 1000
    attack_episodes_per_generation: int = 20
    fraud_rate_target: float = 0.01
    label_delay_enabled: bool = True
    label_delay_hours_mean: float = 48.0
    label_delay_hours_std: float = 24.0
    horizon_days: int = 45
    # Base rate at which a legitimate captured transaction is nonetheless
    # disputed; every such dispute is friendly fraud (disputed and not fraud).
    friendly_fraud_rate: float = 0.005
    # Fraction of genuine fraud that is never disputed (fraud and not disputed).
    under_report_rate: float = 0.25
    dispute_window_days: int = 120


@dataclass(frozen=True)
class DefenderConfig:
    model_type: str = "lightgbm"
    calibration: str = "isotonic"
    step_up_budget_rate: float = 0.02
    daily_review_capacity: int = 400
    latency_budget_ms: float = 150.0


@dataclass(frozen=True)
class RedTeamConfig:
    mutation_rate: float = 0.2
    crossover_rate: float = 0.1
    elite_archive_size: int = 100
    use_quality_diversity: bool = False


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any] = field(default_factory=dict)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    defender: DefenderConfig = field(default_factory=DefenderConfig)
    red_team: RedTeamConfig = field(default_factory=RedTeamConfig)
    source_path: Path | None = None

    @property
    def config_hash(self) -> str:
        canonical = json.dumps(self.raw, sort_keys=True, separators=(",", ":"))
        return hashlib.blake2b(canonical.encode("utf-8"), digest_size=16).hexdigest()


def _subset(cls, data: dict[str, Any]):
    fields = {f for f in cls.__dataclass_fields__}
    return cls(**{k: v for k, v in data.items() if k in fields})


def load_config(path: str | Path | None = None) -> Config:
    """Load a YAML config, filling defaults for any missing keys."""
    if path is None:
        path = CONFIGS_DIR / "hydraloop.yaml"
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config(
        raw=raw,
        simulation=_subset(SimulationConfig, raw.get("simulation", {})),
        defender=_subset(DefenderConfig, raw.get("defender", {})),
        red_team=_subset(RedTeamConfig, raw.get("red_team", {})),
        source_path=path,
    )
