import numpy as np

from hydraloop.twin.labels import LabelModel


def _model(**kw):
    base = dict(
        delay_hours_mean=48,
        delay_hours_std=24,
        friendly_fraud_rate=0.01,
        under_report_rate=0.25,
        dispute_window_days=120,
    )
    base.update(kw)
    return LabelModel(**base)


def test_uncaptured_never_disputed():
    m = _model()
    out = m.resolve(is_fraud=True, captured=False, settlement_ts=0.0, gen=np.random.default_rng(0))
    assert out.disputed is False
    assert out.dispute_ts is None


def test_unreported_fraud_exists():
    m = _model(under_report_rate=1.0)
    out = m.resolve(is_fraud=True, captured=True, settlement_ts=0.0, gen=np.random.default_rng(0))
    # Every fraud is under-reported: fraud and not disputed.
    assert out.is_fraud is True
    assert out.disputed is False


def test_friendly_fraud_exists():
    m = _model(friendly_fraud_rate=1.0)
    out = m.resolve(is_fraud=False, captured=True, settlement_ts=0.0, gen=np.random.default_rng(1))
    # Legit but disputed: friendly fraud.
    assert out.is_fraud is False
    assert out.disputed is True


def test_dispute_window_enforced():
    # A tiny window forces every dispute to lapse.
    m = _model(dispute_window_days=0, friendly_fraud_rate=1.0)
    out = m.resolve(is_fraud=False, captured=True, settlement_ts=0.0, gen=np.random.default_rng(2))
    assert out.disputed is False


def test_fraud_mostly_disputed():
    m = _model(under_report_rate=0.0)
    disputes = 0
    for i in range(200):
        out = m.resolve(True, True, 0.0, np.random.default_rng(i))
        disputes += out.disputed
    assert disputes > 150  # most fraud is caught by disputes when not under-reported
