from app.core.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_blocks_after_max_and_recovers():
    c = Clock()
    lim = SlidingWindowLimiter(3, 60, clock=c)
    for _ in range(3):
        assert not lim.is_blocked("a")
        lim.record("a")
    assert lim.is_blocked("a") and not lim.is_blocked("b")
    assert lim.retry_after("a") == 60
    c.t = 30
    assert lim.retry_after("a") == 30
    c.t = 61
    assert not lim.is_blocked("a") and lim.retry_after("a") == 0


def test_reset_clears_key():
    lim = SlidingWindowLimiter(1, 60, clock=Clock())
    lim.record("a")
    assert lim.is_blocked("a")
    lim.reset("a")
    assert not lim.is_blocked("a")


def test_try_record_counts_until_the_limit_then_refuses_without_counting():
    c = Clock()
    lim = SlidingWindowLimiter(2, 60, clock=c)
    assert lim.try_record("a") and lim.try_record("a")
    assert not lim.try_record("a") and not lim.try_record("a")
    assert lim.retry_after("a") == 60
    c.t = 61  # refused attempts were not counted, so the window drains on schedule
    assert lim.try_record("a")


def test_try_record_is_atomic_across_threads():
    import threading

    lim = SlidingWindowLimiter(5, 900)
    barrier = threading.Barrier(40)
    allowed = []

    def attempt():
        barrier.wait()
        if lim.try_record("victim"):
            allowed.append(1)

    threads = [threading.Thread(target=attempt) for _ in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(allowed) == 5


def test_tracked_keys_stay_bounded_and_expired_keys_go_first():
    c = Clock()
    lim = SlidingWindowLimiter(1, 60, clock=c, max_keys=10)
    for i in range(10):
        lim.record(f"old{i}")
    c.t = 61  # all ten have expired
    lim.record("fresh")
    assert set(lim._events) == {"fresh"}
    for i in range(100):  # a flood of live keys cannot grow the table past the cap
        lim.record(f"flood{i}")
        assert len(lim._events) <= 10
    assert lim.is_blocked("flood99")  # the newest keys are the ones kept
