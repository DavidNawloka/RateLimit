from fastapi import FastAPI

from .middleware import RateLimitMiddleware
from .limiter import TokenBucketLimiter

app = FastAPI()

app.add_middleware(
    RateLimitMiddleware,
    default=TokenBucketLimiter(capacity=10, refill_rate=1.0),
    per_path={
        "/login": TokenBucketLimiter(capacity=3, refill_rate=0.1),
    }
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/search")
async def search(query: str = ""):
    return {"query": query, "results": []}

@app.post("/login")
async def login():
    return {"status": "ok"}
