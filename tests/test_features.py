from hydraloop.twin.entities import Cardholder
from hydraloop.twin.online import EntityState, snapshot_features
from hydraloop.twin.schema import AuthRequest, Channel


def _holder() -> Cardholder:
    return Cardholder(
        cardholder_id="c1",
        created_ts=0.0,
        home_geo=1,
        age_band="35_44",
        balance_minor=100000,
        limit_minor=200000,
        activity_rate_per_day=1.0,
        diurnal_peak_hour=13.0,
        mcc_weights={5411: 1.0},
        device_ids=["d1"],
        payee_ids=["p1"],
        channel_weights={"a2a": 1.0},
    )


def _auth(ts: float, amount: int, device="d1", payee="p1") -> AuthRequest:
    return AuthRequest(
        txn_id="t",
        session_id="s",
        ts=ts,
        cardholder_id="c1",
        device_id=device,
        merchant_id="m1",
        payee_id=payee,
        channel=Channel.A2A,
        amount_minor=amount,
        mcc=5411,
    )


def test_cold_start_flags():
    st = EntityState(created_ts=0.0)
    f = snapshot_features(st, _holder(), _auth(3600.0, 5000), as_of=3600.0)
    assert f["account_is_new"] == 1.0
    assert f["amount_zscore"] is None
    assert f["amount_z_is_new"] == 1.0
    assert f["device_is_new"] == 1.0


def test_zscore_zero_variance():
    st = EntityState(created_ts=0.0)
    for i in range(5):
        st.observe(ts=float(i * 3600), amount=5000.0, device_id="d1", payee_id="p1")
    f = snapshot_features(st, _holder(), _auth(6 * 3600.0, 5000), as_of=6 * 3600.0)
    # Constant amount history -> variance zero -> z-score guarded to 0.0, not NaN.
    assert f["amount_zscore"] == 0.0


def test_velocity_windows():
    st = EntityState(created_ts=0.0)
    now = 10 * 86400.0
    st.observe(now - 1800, 1000.0, "d1", "p1")   # within 1h
    st.observe(now - 5 * 3600, 1000.0, "d1", "p1")  # within 24h not 1h
    st.observe(now - 3 * 86400, 1000.0, "d1", "p1")  # within 7d not 24h
    f = snapshot_features(st, _holder(), _auth(now, 1000), as_of=now)
    assert f["velocity_1h"] == 1.0
    assert f["velocity_24h"] == 2.0
    assert f["velocity_7d"] == 3.0


def test_window_coverage():
    st = EntityState(created_ts=0.0)
    f = snapshot_features(st, _holder(), _auth(3 * 86400.0, 1000), as_of=3 * 86400.0)
    # Only 3 days of history exist against a 7-day window.
    assert 0.0 < f["window_coverage_7d"] < 1.0
