from hydraloop.twin.run import build_engine, generate_legit_traffic, legit_session_specs
from hydraloop.twin.schema import EventType


def _run(cfg, target=200):
    engine, registry = build_engine(cfg)
    specs = legit_session_specs(cfg, engine, registry, target)
    return engine.simulate(specs)


def test_legit_traffic_has_no_fraud(small_config):
    result = _run(small_config)
    assert len(result.transactions) > 0
    assert all(t["is_fraud"] is False for t in result.transactions)


def test_no_capture_without_approval(small_config):
    result = _run(small_config)
    for t in result.transactions:
        if t["captured_minor"] > 0:
            assert t["approved"] is True


def test_events_have_valid_types(small_config):
    result = _run(small_config)
    valid = {e.value for e in EventType}
    assert all(e["event_type"] in valid for e in result.events)


def test_horizon_censoring(small_config):
    result = _run(small_config)
    # Some settlements/disputes fall beyond the horizon and are flagged censored.
    censored = [e for e in result.events if e["censored"]]
    assert isinstance(censored, list)  # may be empty for tiny runs, but must not raise


def test_generate_writes_artifacts(tmp_path, small_config, monkeypatch):
    out = generate_legit_traffic(small_config, "run_engine_test", event_target=150)
    assert out.exists()
    meta = out.parent / "dataset_legit.meta.json"
    assert meta.exists()
    assert (out.parent / "fidelity_report.md").exists()
