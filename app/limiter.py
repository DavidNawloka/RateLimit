from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass
class _Bucket:
    tokens: float
    updated_at: float

class TokenBucketLimiter:
    def __init__(
            self,
            capacity: int,
            refill_rate: float,
            clock: Callable[[], float] = monotonic,
    ) -> None:
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("Capacity and Refill Rate must be positive")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, float, int]:
        with self._lock:
            now = self._clock()
            bucket = self._buckets.get(key)

            if bucket is None:
                bucket = _Bucket(tokens=float(self.capacity), updated_at=now)
                self._buckets[key] = bucket
            else:
                elapsed = now - bucket.updated_at
                bucket.tokens = min(
                    float(self.capacity),
                    bucket.tokens + self.refill_rate * elapsed
                )
                bucket.updated_at = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True, 0.0, int(bucket.tokens)

            retry_after = (1 - bucket.tokens) / self.refill_rate
            return False, retry_after, int(bucket.tokens)
