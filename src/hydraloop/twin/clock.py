"""A seeded discrete-event clock.

Events are ordered by timestamp, with a monotonically increasing sequence
number as the tie-break. Without that tie-break, two events scheduled for the
same instant could pop in a different order from run to run, which would make
the golden-run digest flap.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class _QueueItem:
    ts: float
    seq: int
    payload: Any = field(compare=False, default=None)


class EventClock:
    def __init__(self) -> None:
        self._heap: list[_QueueItem] = []
        self._counter = itertools.count()
        self._now = 0.0

    @property
    def now(self) -> float:
        return self._now

    def schedule(self, ts: float, payload: Any) -> None:
        if ts < self._now:
            raise ValueError(f"cannot schedule into the past: ts={ts} < now={self._now}")
        heapq.heappush(self._heap, _QueueItem(ts, next(self._counter), payload))

    def __bool__(self) -> bool:
        return bool(self._heap)

    def pop(self) -> tuple[float, Any]:
        item = heapq.heappop(self._heap)
        self._now = item.ts
        return item.ts, item.payload

    def __len__(self) -> int:
        return len(self._heap)
