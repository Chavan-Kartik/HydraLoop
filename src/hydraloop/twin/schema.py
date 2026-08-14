"""Event and transaction schema for the twin.

Monetary values are integer *minor units* (e.g. cents) everywhere to avoid
floating-point drift when values are summed, laddered, or refunded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    SESSION_START = "SESSION_START"
    DEVICE_FINGERPRINT = "DEVICE_FINGERPRINT"
    INTENT = "INTENT"
    AUTH_REQUEST = "AUTH_REQUEST"
    RISK_DECISION = "RISK_DECISION"
    THREE_DS_CHALLENGE = "THREE_DS_CHALLENGE"
    CHALLENGE_RESULT = "CHALLENGE_RESULT"
    AUTH_RESPONSE = "AUTH_RESPONSE"
    CAPTURE = "CAPTURE"
    SETTLEMENT = "SETTLEMENT"
    REFUND = "REFUND"
    DISPUTE_OPENED = "DISPUTE_OPENED"
    CHARGEBACK = "CHARGEBACK"
    REPRESENTMENT = "REPRESENTMENT"


class Channel(StrEnum):
    A2A = "a2a"
    WALLET = "wallet"
    CARD_NOT_PRESENT = "card_not_present"


class Action(StrEnum):
    APPROVE = "approve"
    STEP_UP_3DS = "step_up_3ds"
    SOFT_WARN = "soft_warn"
    DELAY_HOLD = "delay_hold"
    MANUAL_REVIEW = "manual_review"
    DECLINE = "decline"


# Lifecycle transitions that the state machine permits. Anything else raises.
ALLOWED_TRANSITIONS: dict[EventType, set[EventType]] = {
    EventType.SESSION_START: {EventType.DEVICE_FINGERPRINT},
    EventType.DEVICE_FINGERPRINT: {EventType.INTENT},
    EventType.INTENT: {EventType.AUTH_REQUEST},
    EventType.AUTH_REQUEST: {EventType.RISK_DECISION},
    EventType.RISK_DECISION: {
        EventType.THREE_DS_CHALLENGE,
        EventType.AUTH_RESPONSE,
    },
    EventType.THREE_DS_CHALLENGE: {EventType.CHALLENGE_RESULT},
    EventType.CHALLENGE_RESULT: {EventType.AUTH_RESPONSE},
    EventType.AUTH_RESPONSE: {EventType.CAPTURE},
    EventType.CAPTURE: {EventType.SETTLEMENT},
    EventType.SETTLEMENT: {
        EventType.REFUND,
        EventType.DISPUTE_OPENED,
    },
    EventType.REFUND: set(),
    EventType.DISPUTE_OPENED: {EventType.CHARGEBACK},
    EventType.CHARGEBACK: {EventType.REPRESENTMENT},
    EventType.REPRESENTMENT: set(),
}


@dataclass(frozen=True)
class Event:
    """One entry in the lifecycle log."""

    event_id: int
    txn_id: str
    session_id: str
    ts: float  # seconds since simulation epoch
    event_type: EventType
    cardholder_id: str
    detail: dict[str, Any] = field(default_factory=dict)
    censored: bool = False

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["event_type"] = self.event_type.value
        row["detail"] = self.detail
        return row


@dataclass(frozen=True)
class AuthRequest:
    """The context available at decision time for one authorisation attempt."""

    txn_id: str
    session_id: str
    ts: float
    cardholder_id: str
    device_id: str
    merchant_id: str
    payee_id: str | None
    channel: Channel
    amount_minor: int
    mcc: int
    currency: str = "XSY"  # synthetic currency code; not a real ISO code


def validate_event_row(row: dict[str, Any]) -> None:
    required = {"event_id", "txn_id", "session_id", "ts", "event_type", "cardholder_id"}
    missing = required - set(row)
    if missing:
        raise ValueError(f"event missing fields {sorted(missing)}")
    if row["event_type"] not in {e.value for e in EventType}:
        raise ValueError(f"unknown event_type {row['event_type']!r}")
    amt = row.get("detail", {}).get("amount_minor")
    if amt is not None and not isinstance(amt, int):
        raise ValueError("amount_minor must be an integer (minor units)")
