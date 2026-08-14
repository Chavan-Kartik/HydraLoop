import pytest
from fastapi.testclient import TestClient

from hydraloop.api import app as app_module
from hydraloop.api import ledger_source
from hydraloop.loop.ledger import GenerationLedger


@pytest.fixture
def seeded_run(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    (runs_dir / "demo_run").mkdir(parents=True)
    monkeypatch.setattr(ledger_source, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(ledger_source, "EXAMPLES_DIR", tmp_path / "examples")

    led = GenerationLedger(runs_dir / "demo_run" / "generation_ledger.jsonl")
    led.append(
        {
            "generation": 1,
            "escape_rate": 1.0,
            "escapes": 40,
            "n_genomes": 8,
            "candidate_archive_recall": 0.0,
            "incumbent_archive_recall": 0.0,
            "promoted": True,
            "escape_clusters": [{"dominant_attack_id": "AF-01", "size": 24}],
            "gate_events": [{"candidate": "immune-memory-retrain", "result": "bootstrap", "promoted": True}],
        }
    )
    led.append(
        {
            "generation": 2,
            "escape_rate": 0.1,
            "escapes": 4,
            "n_genomes": 16,
            "candidate_archive_recall": 0.42,
            "incumbent_archive_recall": 0.61,
            "promoted": False,
            "escape_clusters": [{"dominant_attack_id": "AF-10", "size": 5}],
            "gate_events": [{"candidate": "immune-memory-retrain", "result": "REJECT: regressed", "promoted": False}],
        }
    )
    return "demo_run"


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_health_and_runs(client, seeded_run):
    assert client.get("/api/health").json()["status"] == "ok"
    runs = client.get("/api/runs").json()["runs"]
    assert any(r["run_id"] == seeded_run for r in runs)


def test_scoreboard_series(client, seeded_run):
    data = client.get(f"/api/scoreboard/{seeded_run}").json()
    assert [p["generation"] for p in data["points"]] == [1, 2]
    assert data["points"][0]["escape_rate"] == 1.0
    assert len(data["gauntlet_log"]) == 2


def test_missing_run_is_empty_not_error(client, seeded_run):
    data = client.get("/api/ledger/does_not_exist").json()
    assert data["entries"] == []


def test_ws_streams_in_order_and_completes(client, seeded_run):
    with client.websocket_connect(f"/ws/arena/{seeded_run}?since=-1&tick_ms=0") as ws:
        seqs, kinds = [], []
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "complete":
                break
            seqs.append(msg["seq"])
            kinds.append(msg["type"])
        assert seqs == sorted(seqs)
        assert kinds[0] == "generation_start"
        assert "escape" in kinds and "gauntlet" in kinds


def test_ws_resume_from_sequence(client, seeded_run):
    with client.websocket_connect(f"/ws/arena/{seeded_run}?since=2&tick_ms=0") as ws:
        first = ws.receive_json()
        # Resuming from seq 2 means the next delivered event is seq 3.
        assert first["seq"] == 3
