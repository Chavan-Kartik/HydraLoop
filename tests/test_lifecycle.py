import pytest

from hydraloop.twin.lifecycle import LifecycleError, TransactionState, assert_transition
from hydraloop.twin.schema import EventType


def test_capture_requires_approved_auth():
    tx = TransactionState(1000)
    with pytest.raises(LifecycleError):
        tx.capture(1000)


def test_chargeback_requires_capture():
    tx = TransactionState(1000)
    tx.approve()
    with pytest.raises(LifecycleError):
        tx.open_dispute()


def test_refund_cannot_exceed_capture():
    tx = TransactionState(1000)
    tx.approve()
    tx.capture(600)
    with pytest.raises(LifecycleError):
        tx.refund(700)


def test_dispute_then_chargeback_ok():
    tx = TransactionState(1000)
    tx.approve()
    tx.capture(1000)
    tx.open_dispute()
    tx.chargeback()
    assert tx.charged_back
    assert tx.net_settled_minor == 1000


def test_illegal_transition_raises():
    with pytest.raises(LifecycleError):
        assert_transition(EventType.AUTH_REQUEST, EventType.CAPTURE)


def test_must_start_with_session_start():
    with pytest.raises(LifecycleError):
        assert_transition(None, EventType.AUTH_REQUEST)


def test_amount_must_be_positive():
    with pytest.raises(LifecycleError):
        TransactionState(0)
