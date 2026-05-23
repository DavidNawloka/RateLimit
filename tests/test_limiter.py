from app.limiter import TokenBucketLimiter, SweepConfig
import pytest

class FakeClock:
    def __init__(self, time: float = 0.0):
        self._time = time
    def __call__(self) -> float:
        return self._time
    def tick(self, seconds: float) -> None:
        self._time += seconds

def test_burst_up_to_capacity_then_rejects():
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=3, refill_rate=1.0, clock=clock)

    for i in range(3):
        assert limiter.allow("client-a").allowed

    decision = limiter.allow("client-a")
    assert not decision.allowed
    assert decision.retry_after > 0

def test_tokens_refill_over_time():
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=2, refill_rate=1.0, clock=clock)

    # drain bucket
    limiter.allow("client-a")
    limiter.allow("client-a")
    assert not limiter.allow("client-a").allowed

    # advance 1 seconds therefore fill one token
    clock.tick(1.0)

    assert limiter.allow("client-a").allowed
    assert not limiter.allow("client-a").allowed

def test_refill_capped_at_capacity():
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=2, refill_rate=1.0, clock=clock)

    limiter.allow("client-a")
    clock.tick(10000)

    # make sure that the bucket has not been filled beyond capacity
    assert limiter.allow("client-a").allowed
    assert limiter.allow("client-a").allowed
    assert not limiter.allow("client-a").allowed

def test_clients_have_independent_buckets():
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=1, refill_rate=1.0, clock=clock)
    assert limiter.allow("client-a").allowed
    assert not limiter.allow("client-a").allowed

    assert limiter.allow("client-b").allowed

def test_invalid_clock():
    clock = FakeClock(100.0)
    limiter = TokenBucketLimiter(capacity=2, refill_rate=1.0, clock=clock)
    limiter.allow("client-a")
    clock._time = 50.0 # going backwards in time
    decision = limiter.allow("client-a")

    assert decision.allowed
    assert decision.remaining_tokens == 0

@pytest.mark.parametrize("capacity, refill_rate", [(0, 1.0), (-1, 1.0), (1, 0.0), (1, -1.0)])
def test_invalid_constructor_args(capacity, refill_rate):
    with pytest.raises(ValueError):
        TokenBucketLimiter(capacity, refill_rate)

def test_idle_buckets_are_swept():
    clock = FakeClock()
    limiter = TokenBucketLimiter(
        capacity=2, refill_rate=1.0, clock=clock,
        sweep_config=SweepConfig(min_size=1, call_interval=1),
    )
    for i in range(5):
        limiter.allow(f"client-{i}")
    clock.tick(10.0)
    limiter.allow("trigger-sweep")
    assert set(limiter._buckets.keys()) == {"trigger-sweep"} # makes sure every other bucket has been cleared


def test_partially_refilled_bucket_not_swept_with_slow_refill():
    clock = FakeClock()
    limiter = TokenBucketLimiter(
        capacity=10, refill_rate=0.1, clock=clock,
        sweep_config=SweepConfig(min_size=1, call_interval=1),
    )
    limiter.allow("a")
    clock.tick(5.0)
    limiter.allow("b")  # triggers sweep
    assert "a" in limiter._buckets  # a should still be tracked