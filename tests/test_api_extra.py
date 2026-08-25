"""Endpoint tests for the expanded command center: threats, lineage, governance."""

from __future__ import annotations

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
            "promoted": True,
            "candidate_archive_recall": 0.0,
            "escape_clusters": [{"dominant_attack_id": "AF-01", "dominant_genome": "g1", "size": 24}],
            "gate_events": [{"candidate": "bootstrap", "result": "bootstrap", "promoted": True}],
        }
    )
    led.append(
        {
            "generation": 2,
            "escape_rate": 0.1,
            "escapes": 4,
            "promoted": False,
            "candidate_archive_recall": 0.55,
            "escape_clusters": [{"dominant_attack_id": "AF-01", "dominant_genome": "g2", "size": 5}],
            "gate_events": [{"candidate": "retrain", "result": "REJECT: regressed", "promoted": False}],
        }
    )
    return "demo_run"


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_threats_grouped_by_family(client):
    data = client.get("/api/threats").json()
    assert data["total"] == 28
    families = {f["family"] for f in data["families"]}
    assert "agentic_commerce" in families
    assert all(f["count"] == 4 for f in data["families"])


def test_lineage_links_same_family_across_generations(client, seeded_run):
    data = client.get(f"/api/lineage/{seeded_run}").json()
    assert len(data["nodes"]) == 2
    # AF-01 appears in both generations, so there is one connecting edge.
    assert len(data["edges"]) == 1
    assert data["edges"][0]["attack_id"] == "AF-01"


def test_governance_verifies_clean_chain(client, seeded_run):
    data = client.get(f"/api/governance/{seeded_run}").json()
    assert data["verified"] is True
    assert data["length"] == 2
    assert all(e["link_ok"] for e in data["entries"])


def test_governance_detects_tampering(client, seeded_run, tmp_path):
    path = tmp_path / "runs" / "demo_run" / "generation_ledger.jsonl"
    text = path.read_text(encoding="utf-8").replace('"escape_rate": 1.0', '"escape_rate": 0.0')
    path.write_text(text, encoding="utf-8")
    data = client.get(f"/api/governance/{seeded_run}").json()
    assert data["verified"] is False
    assert data["break_at"] == 0


def test_kpis_summarise_run(client, seeded_run):
    data = client.get(f"/api/kpis/{seeded_run}").json()
    assert data["generations"] == 2
    assert data["escape_rate_start"] == 1.0
    assert data["escape_rate_end"] == 0.1
    assert data["rollbacks"] == 1
    assert data["promotions"] == 1


def test_strategist_never_requires_an_api_key(client, seeded_run):
    data = client.get(f"/api/strategist/{seeded_run}").json()
    assert data["requires_api_key"] is False
    assert data["default_mode"] == "constrained_planner"
    verbs = [s["verb"] for s in data["pipeline"]]
    assert verbs == ["Identify", "Generate", "Defend"]
    assert "genome" in data["guardrail"]
