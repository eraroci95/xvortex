import threading
from collections.abc import Callable


class Slots:
    """Context manager that lets at most `size()` threads inside at once; the others wait.

    The size is read on first use, so settings are not touched at import time.
    """

    def __init__(self, size: Callable[[], int]):
        self._size = size
        self._sem: threading.BoundedSemaphore | None = None
        self._guard = threading.Lock()

    def _semaphore(self) -> threading.BoundedSemaphore:
        with self._guard:
            if self._sem is None:
                self._sem = threading.BoundedSemaphore(max(1, self._size()))
            return self._sem

    def __enter__(self) -> None:
        self._semaphore().acquire()

    def __exit__(self, *exc: object) -> None:
        self._semaphore().release()
