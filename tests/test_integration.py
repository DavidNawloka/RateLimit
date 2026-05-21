import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.limiter import TokenBucketLimiter
from app.middleware import RateLimitMiddleware


@pytest.fixture
def make_app():
    def _build(default: TokenBucketLimiter, per_path: dict[str, TokenBucketLimiter] | None = None) -> TestClient:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, default=default, per_path=per_path)
        @app.get("/")
        async def root():
            return {"ok": True}
        @app.get("/search")
        async def search():
            return {"ok": True}
        return TestClient(app)
    return _build

def test_first_n_requests_pass_then_429(make_app):
    client = make_app(TokenBucketLimiter(capacity=3, refill_rate=0.001))
    for i in range(3):
        assert client.get("/").status_code == 200
    response = client.get("/")
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}

def test_429_includes_retry_after_and_rate_limit_headers(make_app):
    client = make_app(TokenBucketLimiter(capacity=1, refill_rate=0.001))
    client.get("/")
    response = client.get("/")
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1
    assert response.headers["X-RateLimit-Limit"] == "1"
    assert response.headers["X-RateLimit-Remaining"] == "0"


def test_allowed_response_includes_rate_limit_headers(make_app):
    client = make_app(TokenBucketLimiter(capacity=5, refill_rate=1.0))
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert int(response.headers["X-RateLimit-Remaining"]) == 4
    assert "X-RateLimit-Reset" in response.headers


def test_per_path_limiter_overrides_default(make_app):
    client = make_app(
        default=TokenBucketLimiter(capacity=100, refill_rate=10.0),
        per_path={"/search": TokenBucketLimiter(capacity=1, refill_rate=0.001)},
    )
    # /search has a tight limit
    assert client.get("/search").status_code == 200
    assert client.get("/search").status_code == 429
    # / has a generous limit and is unaffected
    assert client.get("/").status_code == 200


def test_default_limiter_used_when_path_has_no_override(make_app):
    client = make_app(
        default=TokenBucketLimiter(capacity=1, refill_rate=0.001),
        per_path={"/search": TokenBucketLimiter(capacity=100, refill_rate=10.0)},
    )
    # / uses the default (tight)
    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 429
