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
