"""A short, structural check of the Gate G4 co-evolution driver.

The strict Gate G4 claim (ROI collapse across 15+ generations) is demonstrated
in the committed example artifact; this test keeps CI fast by asserting the
driver runs end-to-end and produces a well-formed curve.
"""

from __future__ import annotations

import json

from hydraloop.red.coevolution import run_coevolution_economics


def test_short_coevolution_produces_wellformed_curve(small_config):
    path = run_coevolution_economics(
        small_config, run_id="test_evolve", generations=3,
        qd_iterations=4, n_episodes=15, bandit_rounds=4,
    )
    summary = json.loads(path.read_text(encoding="utf-8"))
    assert len(summary["curve"]) == 3
    for point in summary["curve"]:
        assert 0.0 <= point["coverage"] <= 1.0
        assert point["best_roi"] >= 0.0
        assert 0.0 <= point["best_friction_rate"] <= 1.0
    # Every strategist proposal is audited.
    assert summary["audit_entries"] >= 3
