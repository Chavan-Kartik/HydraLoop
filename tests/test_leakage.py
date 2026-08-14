from hydraloop.blue.features import FORBIDDEN_FEATURES, MODEL_FEATURES
from hydraloop.twin.online import FEATURE_COLUMNS


def test_no_future_leakage():
    # No model feature may be a post-decision (future) field.
    assert set(MODEL_FEATURES).isdisjoint(FORBIDDEN_FEATURES)


def test_model_features_are_the_frozen_snapshot():
    # The model may only consume the point-in-time snapshot the twin froze.
    assert set(MODEL_FEATURES) == set(FEATURE_COLUMNS)


def test_forbidden_set_covers_outcome_columns():
    for col in ["approved", "captured_minor", "settled", "dispute_ts", "is_fraud"]:
        assert col in FORBIDDEN_FEATURES
