from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass
class _Bucket:
    tokens: float
    updated_at: float

@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: float
    remaining_tokens: int

@dataclass(frozen=True)
class SweepConfig:
    min_size: int = 1024 # minimum dict size for sweeping
    call_interval: int = 1024 # minimum calls between sweep attempts

class TokenBucketLimiter:
    """Token bucket rate limiter

    Allows request bursts up to 'capacity' and refills at 'refill_rate' tokens/sec.
    In-memory/thread-safe
    """
    def __init__(
            self,
            capacity: int,
            refill_rate: float,
            clock: Callable[[], float] = monotonic,
            sweep_config: SweepConfig = SweepConfig()
    ) -> None:
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("Capacity and Refill Rate must be positive")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = Lock()
        self._sweep_config = sweep_config
        self._calls_since_sweep = 0

    def allow(self, key: str) -> Decision:
        """Tries to consume one token for 'key' (client identification) if still available

        If allowed 'retry_after' in return type will be 0 else seconds until next token available
        """
        with self._lock:
            self._sweep()
            now = self._clock()
            bucket = self._buckets.get(key)

            if bucket is None:
                bucket = _Bucket(tokens=float(self.capacity), updated_at=now)
                self._buckets[key] = bucket
            else:
                elapsed = max(0.0, now - bucket.updated_at) # as clock is injectable, protects against clock problems
                bucket.tokens = min(
                    float(self.capacity),
                    bucket.tokens + self.refill_rate * elapsed
                )
                bucket.updated_at = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return Decision(True, 0.0, int(bucket.tokens))

            retry_after = (1 - bucket.tokens) / self.refill_rate
            return Decision(False, retry_after, int(bucket.tokens))

    def _sweep(self) -> None:
        self._calls_since_sweep += 1
        if self._calls_since_sweep < self._sweep_config.call_interval or len(self._buckets) < self._sweep_config.min_size:
            return

        new_dict = {}
        now = self._clock()
        for key, bucket in self._buckets.items():
            if bucket.tokens + (now - bucket.updated_at) * self.refill_rate < self.capacity:
                new_dict[key] = bucket

        self._buckets = new_dict

