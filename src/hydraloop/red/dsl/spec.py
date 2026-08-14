"""Gene specification for the Attack Genome DSL.

Every gene is declared here with its type and hard bounds. Validation, mutation
clamping, JSON Schema generation, and the MAP-Elites behaviour descriptors all
read from this one table, so the constrained output space is defined in exactly
one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"

FAMILIES = (
    "synthetic_identity",
    "account_takeover",
    "social_engineering",
    "merchant_abuse",
    "card_testing",
    "money_movement",
)

AGE_BANDS = ("18_24", "25_34", "35_44", "45_54", "55_plus")
AMOUNT_TYPES = ("flat", "ladder", "random")
AMOUNT_BASES = ("balance", "limit")
DEVICE_REUSE = ("victim_device", "new_device", "rotating")
CHANNELS = ("a2a", "wallet", "card_not_present")


@dataclass(frozen=True)
class GeneField:
    """One tunable gene: its kind and the bounds mutation must respect."""

    kind: str  # float | int | bool | categorical | simplex | fraction_ladder
    lo: float | None = None
    hi: float | None = None
    options: tuple[str, ...] | None = None
    members: tuple[str, ...] | None = None  # for simplex
    min_len: int | None = None
    max_len: int | None = None


# group -> field name -> spec
GENE_SPEC: dict[str, dict[str, GeneField]] = {
    "victim_selection": {
        "age_band": GeneField("categorical", options=AGE_BANDS),
        "balance_percentile_lo": GeneField("float", 0.0, 1.0),
        "balance_percentile_hi": GeneField("float", 0.0, 1.0),
        "target_side": GeneField("categorical", options=("victim", "account")),
    },
    "amount_policy": {
        "type": GeneField("categorical", options=AMOUNT_TYPES),
        "base": GeneField("categorical", options=AMOUNT_BASES),
        "steps": GeneField("fraction_ladder", 0.0, 1.0, min_len=1, max_len=6),
        "max_fraction": GeneField("float", 0.0, 1.0),
    },
    "timing_policy": {
        "inter_txn_delay_mu": GeneField("float", 0.0, 12.0),
        "inter_txn_delay_sigma": GeneField("float", 0.05, 3.0),
        "dwell_before_cashout_h": GeneField("float", 0.0, 168.0),
    },
    "device_policy": {
        "reuse": GeneField("categorical", options=DEVICE_REUSE),
        "tamper": GeneField("bool"),
        "device_count": GeneField("int", 1, 20),
    },
    "channel_mix": {
        "weights": GeneField("simplex", members=CHANNELS),
    },
    "network_topology": {
        "mule_fanout": GeneField("int", 0, 20),
        "mule_fanin": GeneField("int", 0, 20),
        "layering_depth": GeneField("int", 0, 6),
    },
    "friction_response": {
        "abandon_prob": GeneField("float", 0.0, 1.0),
        "retry_after_h": GeneField("float", 0.0, 72.0),
        "max_retries": GeneField("int", 0, 10),
    },
    "resource_budget": {
        "mule_accounts": GeneField("int", 0, 50),
        "synthetic_identities": GeneField("int", 0, 50),
        "devices": GeneField("int", 1, 50),
        "operator_hours": GeneField("float", 0.0, 100.0),
    },
}


def default_genes() -> dict[str, Any]:
    """A valid, economically-plausible genome used as a mutation seed."""
    return {
        "victim_selection": {
            "age_band": "45_54",
            "balance_percentile_lo": 0.5,
            "balance_percentile_hi": 0.9,
            "target_side": "account",
        },
        "amount_policy": {
            "type": "ladder",
            "base": "balance",
            "steps": [0.1, 0.3, 0.5],
            "max_fraction": 0.6,
        },
        "timing_policy": {
            "inter_txn_delay_mu": 6.0,
            "inter_txn_delay_sigma": 0.9,
            "dwell_before_cashout_h": 3.0,
        },
        "device_policy": {
            "reuse": "new_device",
            "tamper": False,
            "device_count": 2,
        },
        "channel_mix": {
            "weights": {"a2a": 0.6, "wallet": 0.2, "card_not_present": 0.2},
        },
        "network_topology": {
            "mule_fanout": 3,
            "mule_fanin": 1,
            "layering_depth": 1,
        },
        "friction_response": {
            "abandon_prob": 0.3,
            "retry_after_h": 6.0,
            "max_retries": 2,
        },
        "resource_budget": {
            "mule_accounts": 3,
            "synthetic_identities": 0,
            "devices": 2,
            "operator_hours": 2.0,
        },
    }
