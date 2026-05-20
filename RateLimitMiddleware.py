from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from TokenBucketLimiter import TokenBucketLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            default: TokenBucketLimiter,
            per_path: dict[str, TokenBucketLimiter] | None = None) -> None:
        super().__init__(app)
        self._default = default
        self._per_path = per_path
    def _client_key(self, request: Request) -> str:
        return request.client.host

    async def dispatch(self, request: Request, call_next):
        limiter = self._per_path.get(request.url.path, self._default)
        key = self._client_key(request)

        allowed, retry_after = limiter.allow(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, ceil(retry_after))),
                    "X-RateLimit-Limit": str(limiter._capacity),
                    "X-RateLimit-Remaining": "0",
                })
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter._capacity)
        response.headers["X-RateLimit-Remaining"] = str(limiter.remaining(key))
        return response