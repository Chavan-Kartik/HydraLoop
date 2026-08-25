"""Interactive lab: type a threat, get a full Identify-to-Detect trace."""

import json

from fastapi.testclient import TestClient

from hydraloop.api import app as app_module
from hydraloop.api.lab import PRESETS, iter_lab, run_lab


def test_run_lab_agentic_preset_has_steps_and_cases():
    result = run_lab(PRESETS["agentic"])
    ids = [s["id"] for s in result["steps"]]
    assert ids[:3] == ["identify", "generate", "simulate"]
    assert result["family"] == "agentic_commerce"
    assert result["stats"]["n_txns"] > 0
    assert result["stats"]["n_fraud"] > 0
    assert result["cases"], "lab must return investigation cases"
    assert result["txns"]


def test_lab_endpoint_rejects_tiny_input():
    client = TestClient(app_module.app)
    res = client.post("/api/lab", json={"text": "too short"})
    assert res.status_code == 422


def test_lab_endpoint_accepts_preset(monkeypatch):
    client = TestClient(app_module.app)
    res = client.post("/api/lab", json={"text": PRESETS["testing"]})
    assert res.status_code == 200
    body = res.json()
    assert body["family"] == "card_testing"
    assert len(body["steps"]) >= 4
    assert body["highlights"]


def test_lab_stream_emits_steps_then_done():
    types = []
    result = None
    for ev in iter_lab(PRESETS["agentic"]):
        types.append(ev["type"])
        if ev["type"] == "done":
            result = ev["result"]
    assert types[0] == "status"
    assert "step" in types
    assert "scores" in types
    assert types[-1] == "done"
    assert result and result["cases"]

    client = TestClient(app_module.app)
    with client.stream("POST", "/api/lab/stream", json={"text": PRESETS["testing"]}) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    events = [json.loads(line) for line in body.splitlines() if line.strip()]
    assert events[-1]["type"] == "done"
    assert events[-1]["result"]["family"] == "card_testing"
