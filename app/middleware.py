from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .limiter import TokenBucketLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            default: TokenBucketLimiter,
            per_path: dict[str, TokenBucketLimiter] | None = None) -> None:
        super().__init__(app)
        self._default = default
        self._per_path = per_path or {}

    def _client_key(self, request: Request) -> str:
        # in production I would use some kind of userID/api-token/bearer-token for authenticated endpoints
        # and ip addresses for public endpoints
        if request.client is not None:
            return request.client.host
        else:
            return "unknown"

    async def dispatch(self, request: Request, call_next):
        limiter = self._per_path.get(request.url.path, self._default)
        key = self._client_key(request)

        allowed, retry_after, remaining = limiter.allow(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, ceil(retry_after))),
                    "X-RateLimit-Limit": str(limiter.capacity),
                    "X-RateLimit-Remaining": "0",
                })
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response