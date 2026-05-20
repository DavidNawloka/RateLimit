from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass
class Bucket:
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
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._buckets: dict[str, Bucket] = {}
        self._lock = Lock()

    def allow(self, key:str) -> tuple[bool, float]:

        with self._lock:
            now = self._clock()
            bucket = self._buckets.get(key)

            if bucket is None:
                bucket = Bucket(tokens=float(self._capacity), updated_at=now)
                self._buckets[key] = bucket
            else:
                elapsed = now - bucket.updated_at
                bucket.tokens = min(
                    float(self._capacity),
                    bucket.tokens + self._refill_rate * elapsed
                )
                bucket.updated_at = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True, 0.0

            retry_after = (1-bucket.tokens) / self._refill_rate
            return False, retry_after

    def remaining(self, key:str) -> int:
        bucket = self._buckets.get(key)
        if bucket:
            return int(bucket.tokens)
        else:
            return self._capacity
