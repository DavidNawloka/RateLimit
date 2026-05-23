# Rate Limiter

A small FastAPI project showcasing token-bucket rate limiting as middleware.

## Running

Install [uv](https://github.com/astral-sh/uv), then:

```
uv sync
uv run uvicorn app.main:app --reload
```

The example app in main.py exposes `/`, `/search`, and `/login` with limits wired up through the middleware.

## Tests

```
uv run pytest -q
```

test_limiter.py covers the limiter directly with an injected fake clock. test_integration.py tests the middleware with a test client and asserts status codes and rate-limit headers.

## Design decisions

**Token bucket.** Burst-friendly but on average still provides predictable rate limiting, requires only two parameters (capacity, refill rate). 

**In-memory, single process.** The state lives in a dict on the limiter instance. Scaling would require shared state, maybe via Redis

**One lock per limiter instance.** To ensure consistency during simultaneous calls

**Injectable clock.** Limiter class takes clock as input param, used for testing purposes 

**Per-endpoint limits.** The middleware takes a per_path dict so tighter limits can be applied to specific routes (e.g. /login). Path matching is exact-string; route templates are not supported.

**Client key: IP address.** Used for unauthenticated endpoints. For authenticated endpoints some kind of user ID or api token would be used instead

**Bucket dictionary sweeps.** Without sweeping, bucket dictionary would grow indefinitely (memory leak). Therefore, every n calls the dict is checked for full buckets which are then swept

## What I would add next

- User ID/token as client key on authenticated routes
- Router-template path matching so that /user/1 and /user/2 can fall under the same token-bucket
- Look up Redis Docs and check how to implement/use it correctly