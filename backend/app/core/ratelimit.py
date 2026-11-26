import threading
import time
from collections import deque
from collections.abc import Callable
from math import ceil


class SlidingWindowLimiter:
    """In-memory sliding-window counter, safe to call from several threads.

    Per process: adequate for a single Render instance; switch to a shared store (e.g. Redis)
    before running several instances.

    Use `try_record` for gates: it checks and records in one step, so parallel requests cannot all
    pass the check before any of them is counted. Memory is bounded: past `max_keys` tracked keys,
    expired keys are dropped first, then the oldest-seen keys.
    """

    def __init__(
        self, max_events: int, window_seconds: float,
        clock: Callable[[], float] = time.monotonic, max_keys: int = 10_000,
    ):
        self.max_events = max_events
        self.window = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    # The helpers below assume the caller holds self._lock.

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

    def _make_room(self) -> None:
        for k in list(self._events):
            self._prune(k)
        target = self.max_keys - max(1, self.max_keys // 10)  # leave headroom so this runs rarely
        while len(self._events) > target:
            del self._events[next(iter(self._events))]

    def _append(self, key: str) -> None:
        if key not in self._events and len(self._events) >= self.max_keys:
            self._make_room()
        self._events.setdefault(key, deque()).append(self._clock())

    # Public API.

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            q = self._prune(key)
            return q is not None and len(q) >= self.max_events

    def retry_after(self, key: str) -> int:
        with self._lock:
            q = self._prune(key)
            if q is None or len(q) < self.max_events:
                return 0
            return max(1, ceil(q[0] + self.window - self._clock()))

    def record(self, key: str) -> None:
        """Count an event unconditionally."""
        with self._lock:
            self._append(key)

    def try_record(self, key: str) -> bool:
        """Count an event unless the key is already at its limit. Returns whether it was counted."""
        with self._lock:
            q = self._prune(key)
            if q is not None and len(q) >= self.max_events:
                return False
            self._append(key)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
