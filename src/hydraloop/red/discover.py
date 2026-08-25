"""Identify-as-discovery: turn an abstract threat writeup into a live attack.

The challenge asks us to *identify emerging* GenAI fraud, not just catalog it. This
module closes that loop: it ingests a short, abstract description of an emerging
threat (e.g. a paragraph from a fraud-trends writeup) and maps it into a
schema-valid attack genome the twin can immediately simulate. A local language
model does the mapping when available; a deterministic keyword mapper is the
offline fallback so the capability always runs.

Safety is preserved end to end: the output is only bounded genome parameters plus
behavioural signal names - never prose recipes, credentials, or content. The genome
DSL is the guardrail, exactly as in the strategist.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np

from .dsl.genome import Genome, default_genome
from .dsl.render import render_brief
from .dsl.spec import FAMILIES
from .llm import extract_json
from .strategist import _apply_overlay

LLMClient = Callable[[str], str]

# Deterministic keyword -> family mapping for the offline fallback.
_FAMILY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("agentic_commerce", ("agent", "autonomous", "mandate", "checkout bot", "agentic", "delegated")),
    ("synthetic_identity", ("synthetic", "fabricated", "onboarding", "fake identity", "bust-out")),
    ("account_takeover", ("takeover", "credential", "session", "login", "hijack", "stuffing")),
    ("social_engineering", ("scam", "deepfake", "voice", "romance", "impersonat", "push payment", "app scam", "grooming")),
    ("merchant_abuse", ("merchant", "laundering", "chargeback", "refund", "shell")),
    ("card_testing", ("card testing", "enumeration", "probe", "bin range", "validation")),
    ("money_movement", ("mule", "layering", "smurf", "structuring", "cash-out", "fan-out")),
]

_SIGNAL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("inter_arrival_regularity", ("machine", "automat", "cadence", "regular", "rapid", "speed")),
    ("value_escalation", ("escalat", "high value", "drain", "ladder")),
    ("payee_novelty_rate", ("payee", "destination", "new merchant", "redirect")),
    ("device_rotation_rate", ("device", "rotate", "swarm")),
    ("session_automation_signature", ("session", "agent", "bot", "autonomous")),
]


def _fallback_family(text: str) -> str:
    low = text.lower()
    for family, kws in _FAMILY_KEYWORDS:
        if any(k in low for k in kws):
            return family
    return "social_engineering"


def _fallback_signals(text: str) -> list[str]:
    low = text.lower()
    hits = [sig for sig, kws in _SIGNAL_KEYWORDS if any(k in low for k in kws)]
    return hits or ["inter_arrival_regularity"]


def _fallback_overlay(text: str) -> dict:
    """A small, deterministic gene overlay derived from the writeup's tone."""
    low = text.lower()
    overlay: dict = {}
    if any(k in low for k in ("machine", "rapid", "speed", "swarm", "automat")):
        overlay["timing_policy"] = {"inter_txn_delay_mu": 0.5, "dwell_before_cashout_h": 0.25}
    if any(k in low for k in ("high value", "drain", "escalat", "ladder")):
        overlay.setdefault("amount_policy", {})["max_fraction"] = 0.7
    if any(k in low for k in ("device", "rotate", "swarm")):
        overlay["device_policy"] = {"reuse": "rotating", "device_count": 8}
    return overlay


def _prompt(text: str) -> str:
    return (
        "You classify an emerging payment-fraud description into a synthetic lab's "
        "attack schema. Output JSON ONLY with keys: family (one of "
        f"{list(FAMILIES)}), attack_name (short), behavioral_signals (list of "
        "snake_case metadata tokens, no prose), genes (an object overlaying numeric "
        "gene groups such as timing_policy.inter_txn_delay_mu, amount_policy."
        "max_fraction in [0,1], device_policy.device_count). Never output messages, "
        "credentials, or step-by-step instructions - only bounded parameters.\n\n"
        f"DESCRIPTION:\n{text}"
    )


def discover_threat(text: str, rng: np.random.Generator, llm: LLMClient | None = None) -> dict:
    """Map an abstract threat writeup into a validated, simulatable attack genome."""
    method = "fallback"
    family = _fallback_family(text)
    attack_name = "Discovered emerging threat"
    signals = _fallback_signals(text)
    overlay = _fallback_overlay(text)

    if llm is not None:
        cleaned = extract_json(llm(_prompt(text)))
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and data.get("family") in FAMILIES:
                family = data["family"]
                attack_name = str(data.get("attack_name") or attack_name)[:80]
                sig = data.get("behavioral_signals")
                if isinstance(sig, list) and sig:
                    signals = [str(s)[:48] for s in sig][:6]
                if isinstance(data.get("genes"), dict):
                    overlay = data["genes"]
                method = "llm"
        except (json.JSONDecodeError, TypeError):
            method = "fallback"

    # The DSL is the guardrail: clamp whatever we got onto a valid base genome.
    base = default_genome(family=family, attack_id="AF-DISC")
    genome = _apply_overlay(base, overlay if isinstance(overlay, dict) else {})
    genome = Genome(
        family=genome.family, genes=genome.genes, attack_id="AF-DISC",
        label=f"AF-DISC.{method}",
    )
    genome.validate()

    return {
        "source_text": text,
        "method": method,
        "family": family,
        "attack_name": attack_name,
        "behavioral_signals": signals,
        "genome_id": genome.genome_id,
        "brief": render_brief(genome),
        "genes": genome.genes,
    }
