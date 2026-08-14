"""Lifecycle enforcement: legal transitions and monetary invariants.

Illegal transitions raise; they never warn-and-continue. This is what lets the
twin claim that a captured amount always had an approved auth behind it, that a
chargeback always had a capture, and that refunds never exceed what was taken.
"""

from __future__ import annotations

from .schema import ALLOWED_TRANSITIONS, EventType


class LifecycleError(ValueError):
    """Raised on an illegal lifecycle transition or a monetary invariant breach."""


def assert_transition(prev: EventType | None, nxt: EventType) -> None:
    if prev is None:
        if nxt is not EventType.SESSION_START:
            raise LifecycleError(f"a transaction must begin with SESSION_START, not {nxt}")
        return
    allowed = ALLOWED_TRANSITIONS.get(prev, set())
    if nxt not in allowed:
        raise LifecycleError(f"illegal transition {prev} -> {nxt}")


class TransactionState:
    """Tracks money and lifecycle position for one transaction."""

    def __init__(self, amount_minor: int) -> None:
        if amount_minor <= 0:
            raise LifecycleError("transaction amount must be a positive integer (minor units)")
        self.amount_minor = amount_minor
        self.captured_minor = 0
        self.refunded_minor = 0
        self.approved = False
        self.disputed = False
        self.charged_back = False
        self._last: EventType | None = None

    def advance(self, nxt: EventType) -> None:
        assert_transition(self._last, nxt)
        self._last = nxt

    def approve(self) -> None:
        self.approved = True

    def capture(self, amount_minor: int) -> None:
        if not self.approved:
            raise LifecycleError("cannot capture without an approved authorisation")
        if amount_minor <= 0 or amount_minor > self.amount_minor - self.captured_minor:
            raise LifecycleError("capture exceeds the authorised amount")
        self.captured_minor += amount_minor

    def refund(self, amount_minor: int) -> None:
        if amount_minor <= 0 or amount_minor > self.captured_minor - self.refunded_minor:
            raise LifecycleError("refund cannot exceed the net captured value")
        self.refunded_minor += amount_minor

    def open_dispute(self) -> None:
        if self.captured_minor <= 0:
            raise LifecycleError("cannot dispute a transaction that was never captured")
        self.disputed = True

    def chargeback(self) -> None:
        if not self.disputed:
            raise LifecycleError("cannot charge back without an open dispute")
        self.charged_back = True

    @property
    def net_settled_minor(self) -> int:
        return self.captured_minor - self.refunded_minor
