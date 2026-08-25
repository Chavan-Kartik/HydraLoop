"""Tests for Identify-as-discovery: writeup -> validated attack genome."""

from __future__ import annotations

import json

import numpy as np

from hydraloop.red.discover import discover_threat
from hydraloop.red.dsl.genome import genome_from_dict


def test_fallback_maps_agentic_writeup_to_family():
    text = (
        "An autonomous shopping agent with a delegated mandate drifts beyond its "
        "intended cadence and drains balances at machine speed."
    )
    result = discover_threat(text, np.random.default_rng(0), llm=None)
    assert result["method"] == "fallback"
    assert result["family"] == "agentic_commerce"
    assert result["genome_id"]
    assert result["brief"]
    # The emitted genome must be schema-valid.
    genome_from_dict(
        {"family": result["family"], "genes": result["genes"], "attack_id": "AF-DISC"}
    )


def test_fallback_maps_mule_writeup_to_money_movement():
    result = discover_threat(
        "Funds fan out through mule accounts and layering chains before cash-out.",
        np.random.default_rng(0),
    )
    assert result["family"] == "money_movement"


def test_llm_output_is_used_and_clamped():
    def fake_llm(_prompt: str) -> str:
        # Out-of-bounds max_fraction must be clamped, not rejected.
        return json.dumps(
            {
                "family": "card_testing",
                "attack_name": "GenAI-tuned probing",
                "behavioral_signals": ["low_value_probe_density"],
                "genes": {"amount_policy": {"max_fraction": 5.0}},
            }
        )

    result = discover_threat("probing", np.random.default_rng(0), llm=fake_llm)
    assert result["method"] == "llm"
    assert result["family"] == "card_testing"
    assert result["genes"]["amount_policy"]["max_fraction"] <= 1.0
