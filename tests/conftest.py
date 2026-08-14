import dataclasses

import pytest

from hydraloop.config import Config, DefenderConfig, RedTeamConfig, SimulationConfig


@pytest.fixture
def small_config() -> Config:
    sim = SimulationConfig(
        seed=7,
        generations=2,
        legitimate_transactions_per_generation=300,
        attack_episodes_per_generation=20,
        horizon_days=20,
    )
    return Config(
        raw={"simulation": dataclasses.asdict(sim)},
        simulation=sim,
        defender=DefenderConfig(),
        red_team=RedTeamConfig(),
    )
