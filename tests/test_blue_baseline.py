import json

from hydraloop.blue.run import train_baseline
from hydraloop.paths import run_dir


def test_baseline_beats_rule_and_calibrates(small_config):
    # A small but non-trivial run: enough positives to be meaningful.
    import dataclasses

    from hydraloop.config import Config

    sim = dataclasses.replace(
        small_config.simulation,
        seed=42,
        legitimate_transactions_per_generation=9000,
        attack_episodes_per_generation=140,
        fraud_rate_target=0.02,
        horizon_days=45,
    )
    cfg = Config(raw={}, simulation=sim, defender=small_config.defender, red_team=small_config.red_team)

    out = train_baseline(cfg, "run_blue_test")
    assert out.exists()
    metrics = json.loads((run_dir("run_blue_test") / "metrics.json").read_text())
    # The stable, operationally meaningful claim: in the low-FPR regime a bank
    # actually operates in, ML dominates the velocity rule on ground-truth fraud.
    assert metrics["ml_vs_true"]["recall_at_fpr_1pct"] > metrics["rule_vs_true"]["recall_at_fpr_1pct"]
    assert metrics["ml_vs_true"]["value_detection_rate_at_fpr_1pct"] > metrics["rule_vs_true"][
        "value_detection_rate_at_fpr_1pct"
    ]
    # Calibration reported in two binnings; ECE is scale-dependent (it tightens
    # toward 0.05 with more data) so the test asserts a lenient, reliably-met bar
    # and the report carries the exact figures.
    assert metrics["ece_observed_equal_mass"] < 0.12
