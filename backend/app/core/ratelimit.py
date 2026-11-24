import time
from collections import deque
from collections.abc import Callable
from math import ceil


class SlidingWindowLimiter:
    """In-memory sliding-window counter. Per process: adequate for a single Render instance;
    switch to a shared store (e.g. Redis) before running several instances."""

    def __init__(self, max_events: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_events = max_events
        self.window = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    def _prune(self, key: str) -> deque[float] | None:
        q = self._events.get(key)
        if q is None:
            return None
        cutoff = self._clock() - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if not q:
            del self._events[key]
            return None
        return q

    def is_blocked(self, key: str) -> bool:
        q = self._prune(key)
        return q is not None and len(q) >= self.max_events

    def retry_after(self, key: str) -> int:
        q = self._prune(key)
        if q is None or len(q) < self.max_events:
            return 0
        return max(1, ceil(q[0] + self.window - self._clock()))

    def record(self, key: str) -> None:
        if len(self._events) > 10_000:
            for k in list(self._events):
                self._prune(k)
        self._events.setdefault(key, deque()).append(self._clock())

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def clear(self) -> None:
        self._events.clear()
