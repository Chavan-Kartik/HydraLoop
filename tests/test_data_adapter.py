"""Tests for the external-data credibility bridge."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hydraloop.evaluation.data_adapter import (
    DATASET_PRESETS,
    ColumnMap,
    benchmark,
    load_external_csv,
    make_demo_reference_csv,
    resolve_dataset,
    run_data_benchmark,
    synthetic_and_reference,
)


def test_synthetic_shift_reports_fidelity_and_transfer(small_config):
    synthetic, reference = synthetic_and_reference(small_config, fraud_per_family=30)
    result = benchmark(synthetic, reference, seed=small_config.simulation.seed)

    assert result["shared_feature_count"] == len(
        [c for c in synthetic.columns if c in reference.columns and c in synthetic.columns]
    ) or result["shared_feature_count"] > 0
    # Two twin populations should be hard to separate: AUC well below "easy".
    assert not np.isnan(result["discriminator_auc"])
    assert result["discriminator_auc"] <= 0.9
    # Full features present, so transfer numbers are real, not null.
    assert result["tstr_recall_at_fpr_1pct"] is not None
    assert result["trts_recall_at_fpr_1pct"] is not None


def test_external_csv_roundtrip_and_null_transfer(small_config, tmp_path):
    csv_path = make_demo_reference_csv(tmp_path / "external.csv", small_config, fraud_per_family=15)
    df = load_external_csv(
        csv_path, ColumnMap(amount="amount", timestamp="timestamp", is_fraud="is_fraud")
    )
    assert {"amount_minor", "hour_of_day", "day_of_week", "is_fraud"} <= set(df.columns)
    assert len(df) > 0

    report = run_data_benchmark(
        small_config, external_csv=csv_path, out_dir=tmp_path / "out", fraud_per_family=15
    )
    assert report["mode"].startswith("external_csv")
    # An amount/timestamp-only file cannot support TSTR; it must say so, not fake it.
    assert report["tstr_recall_at_fpr_1pct"] is None
    assert (tmp_path / "out" / "data_benchmark.json").exists()
    assert (tmp_path / "out" / "data_benchmark.md").exists()


def test_missing_preset_degrades_to_synthetic_shift(small_config, tmp_path):
    # A preset whose file is absent must not crash: it falls back and says so.
    report = run_data_benchmark(
        small_config, preset="sparkov", external_csv=str(tmp_path / "nope.csv"),
        out_dir=tmp_path / "out2", fraud_per_family=15,
    )
    assert report["mode"] == "synthetic_shift"
    assert report["reference_source"] == "synthetic_shift"
    assert "not found" in report.get("note", "")


def test_resolve_dataset_reports_missing():
    path, colmap, note = resolve_dataset("sparkov", "definitely_missing.csv")
    assert path is None
    assert colmap == DATASET_PRESETS["sparkov"]
    assert "not found" in note


def test_sparkov_preset_columns_and_epoch_timestamp(small_config, tmp_path):
    # A tiny Sparkov-shaped file loads via the preset column map.
    csv_path = tmp_path / "sparkov.csv"
    pd.DataFrame(
        {
            "amt": [12.5, 300.0, 9.99, 45.0, 1000.0, 5.0],
            "trans_date_trans_time": [
                "2019-01-01 10:00:00", "2019-01-01 22:30:00", "2019-01-02 03:00:00",
                "2019-01-02 14:15:00", "2019-01-03 09:00:00", "2019-01-03 23:59:00",
            ],
            "is_fraud": [0, 1, 0, 0, 1, 0],
        }
    ).to_csv(csv_path, index=False)

    df = load_external_csv(csv_path, DATASET_PRESETS["sparkov"])
    assert {"amount_minor", "hour_of_day", "day_of_week", "is_fraud"} <= set(df.columns)
    assert df["amount_minor"].iloc[0] == 1250.0  # 12.50 major -> minor units
    assert df["hour_of_day"].iloc[1] == 22.0


def test_epoch_hours_timestamp_parsing(tmp_path):
    csv_path = tmp_path / "paysim.csv"
    pd.DataFrame(
        {"amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
         "step": [0, 1, 24, 25, 48, 49],
         "isFraud": [0, 1, 0, 0, 1, 0]}
    ).to_csv(csv_path, index=False)
    df = load_external_csv(csv_path, DATASET_PRESETS["paysim"])
    # step is an hour index: step 24 -> hour-of-day 0 the next day.
    assert df["hour_of_day"].iloc[2] == 0.0
