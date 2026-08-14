from hydraloop.api.hub import EventHub


def test_sequence_numbers_are_monotonic():
    hub = EventHub(capacity=10)
    a = hub.publish({"type": "x"})
    b = hub.publish({"type": "y"})
    assert a.seq == 0 and b.seq == 1
    assert hub.next_seq == 2


def test_replay_since_returns_only_newer():
    hub = EventHub(capacity=10)
    for i in range(5):
        hub.publish({"i": i})
    replay = hub.replay_since(2)
    assert [e.seq for e in replay.events] == [3, 4]
    assert replay.dropped == 0
    assert replay.next_since == 4


def test_drop_oldest_reports_missed_events():
    hub = EventHub(capacity=3)
    for i in range(10):  # ring keeps only seqs 7,8,9
        hub.publish({"i": i})
    assert hub.earliest_seq == 7
    replay = hub.replay_since(-1)  # a fresh client wants everything
    assert [e.seq for e in replay.events] == [7, 8, 9]
    assert replay.dropped == 7  # seqs 0..6 were evicted
