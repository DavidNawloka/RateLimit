from fastapi import FastAPI

from RateLimitMiddleware import RateLimitMiddleware
from TokenBucketLimiter import TokenBucketLimiter

app = FastAPI()

app.add_middleware(
    RateLimitMiddleware,
    default=TokenBucketLimiter(capacity=10, refill_rate=1.0),
    per_path={
        "/login":TokenBucketLimiter(capacity=3, refill_rate=0.1),
    }
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
