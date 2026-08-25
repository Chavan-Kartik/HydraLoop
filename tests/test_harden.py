"""The on-demand closed loop: escape, harden, gauntlet, re-attack.

These tests exist to protect the two properties that make the demo honest: the
verdict is measured on a wave the candidate never trained on, and neither model
is allowed to buy recall by spending more than its false-positive budget.
"""

from __future__ import annotations

import json

import numpy as np
from fastapi.testclient import TestClient

from hydraloop.api import app as app_module
from hydraloop.api.harden import (
    FPR_BUDGET,
    SEED_BASELINE,
    SEED_CALIB,
    SEED_WAVE1,
    SEED_WAVE2,
    _threshold_at_fpr,
    iter_harden,
)
from hydraloop.api.lab import PRESETS


def test_threshold_respects_budget_under_heavy_ties():
    # Isotonic calibration produces plateaus; a plain quantile lands mid-plateau
    # and then flags every tied row. The chosen threshold must never do that.
    scores = np.array([0.1] * 50 + [0.9] * 50)
    thr = _threshold_at_fpr(scores, 0.01)
    assert float(np.mean(scores >= thr)) <= 0.01

    smooth = np.linspace(0.0, 1.0, 1000)
    thr = _threshold_at_fpr(smooth, 0.01)
    assert float(np.mean(smooth >= thr)) <= 0.01


def test_waves_are_independent_draws():
    assert len({SEED_CALIB, SEED_BASELINE, SEED_WAVE1, SEED_WAVE2}) == 4


def test_harden_cycle_is_honest_and_complete():
    events = list(iter_harden(PRESETS["agentic"]))
    kinds = [e["type"] for e in events]

    for required in ("identity", "incumbent", "escape", "candidate", "gauntlet", "verdict", "ledger"):
        assert required in kinds, f"missing stage: {required}"
    assert kinds[-1] == "done"

    result = events[-1]["result"]
    before, after = result["before"], result["after"]

    # The verdict wave must contain both classes, or the comparison is vacuous.
    assert result["n_fraud"] > 0 and result["n_legit"] > 0

    # Neither operating point may exceed the budget by more than sampling noise
    # on the fresh wave. This is the claim a judge is most likely to attack.
    assert before["fpr"] <= FPR_BUDGET * 3
    assert after["fpr"] <= FPR_BUDGET * 3

    # Recall is a rate, and the counts behind it must add up.
    for side in (before, after):
        assert 0.0 <= side["recall"] <= 1.0
        assert side["caught"] + side["escaped"] == result["n_fraud"]

    # The ledger entry is chained, not a loose hash.
    assert len(result["entry_hash"]) == 32


def test_harden_learns_the_zero_day_it_was_shown():
    """Hardening must improve recall on a *fresh* wave of the same attack."""
    result = None
    for ev in iter_harden(PRESETS["testing"]):
        if ev["type"] == "done":
            result = ev["result"]
    assert result is not None
    assert result["after"]["recall"] > result["before"]["recall"], (
        "the retrained candidate did not generalise to unseen rows of the same attack"
    )
    assert result["after"]["escaped_value_minor"] <= result["before"]["escaped_value_minor"]


def test_harden_endpoint_streams_ndjson():
    client = TestClient(app_module.app)
    with client.stream("POST", "/api/harden/stream", json={"text": PRESETS["agentic"]}) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    events = [json.loads(line) for line in body.splitlines() if line.strip()]
    assert events[-1]["type"] == "done"
    assert events[-1]["result"]["family"] == "agentic_commerce"


def test_harden_endpoint_rejects_tiny_input():
    client = TestClient(app_module.app)
    assert client.post("/api/harden/stream", json={"text": "nope"}).status_code == 422
