import pytest

from hydraloop.twin.clock import EventClock


def test_pops_in_time_order():
    c = EventClock()
    for ts in [5.0, 1.0, 3.0, 2.0]:
        c.schedule(ts, ts)
    got = []
    while c:
        _, p = c.pop()
        got.append(p)
    assert got == [1.0, 2.0, 3.0, 5.0]


def test_tiebreak_is_deterministic():
    # Equal timestamps must pop in insertion order via the sequence counter.
    c = EventClock()
    for label in ["a", "b", "c", "d"]:
        c.schedule(10.0, label)
    got = [c.pop()[1] for _ in range(4)]
    assert got == ["a", "b", "c", "d"]


def test_cannot_schedule_into_the_past():
    c = EventClock()
    c.schedule(5.0, "x")
    c.pop()
    with pytest.raises(ValueError):
        c.schedule(1.0, "y")
