import threading
import time

from app.core.concurrency import Slots


def test_slots_cap_how_many_threads_run_at_once():
    slots = Slots(lambda: 2)
    running, peak, lock = 0, 0, threading.Lock()

    def work():
        nonlocal running, peak
        with slots:
            with lock:
                running += 1
                peak = max(peak, running)
            time.sleep(0.03)
            with lock:
                running -= 1

    threads = [threading.Thread(target=work) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert peak == 2 and running == 0


def test_slots_release_when_the_body_raises():
    slots = Slots(lambda: 1)
    try:
        with slots:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    done = []
    t = threading.Thread(target=lambda: (slots.__enter__(), done.append(1), slots.__exit__(None, None, None)))
    t.start()
    t.join(timeout=2)
    assert done == [1]


def test_size_is_read_lazily_and_never_below_one():
    calls = []
    slots = Slots(lambda: calls.append(1) or 0)
    assert calls == []
    with slots:
        pass
    assert calls == [1]
