"""A bounded, sequence-numbered event ring for the arena stream.

Backpressure is drop-oldest: the ring holds only the most recent ``capacity``
events. A client that reconnects with a ``since`` sequence older than what the
ring still holds is told exactly how many events it missed, so the UI can show
an honest "N events dropped" indicator and resume from the oldest live event.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class SeqEvent:
    seq: int
    event: dict


@dataclass
class Replay:
    events: list[SeqEvent]
    dropped: int
    next_since: int


class EventHub:
    def __init__(self, capacity: int = 512) -> None:
        self.capacity = capacity
        self._ring: deque[SeqEvent] = deque(maxlen=capacity)
        self._next_seq = 0

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def earliest_seq(self) -> int:
        return self._ring[0].seq if self._ring else self._next_seq

    def publish(self, event: dict) -> SeqEvent:
        item = SeqEvent(seq=self._next_seq, event=event)
        self._ring.append(item)
        self._next_seq += 1
        return item

    def replay_since(self, since: int) -> Replay:
        """Return events with seq > since, and how many were dropped before them.

        ``dropped`` is non-zero only when the client fell so far behind that the
        ring evicted events it had not yet seen.
        """
        want_from = since + 1
        dropped = max(0, self.earliest_seq - want_from) if self._ring else 0
        events = [e for e in self._ring if e.seq > since]
        next_since = events[-1].seq if events else since
        return Replay(events=events, dropped=dropped, next_since=next_since)
