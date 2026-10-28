import os

import pytest
from redis.asyncio import Redis

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://flowops:flowops@localhost:5432/flowops_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
async def isolate_rate_limit_keys():
    url = os.environ["REDIS_URL"]
    if not url.endswith("/15"):
        raise RuntimeError("Tests require the dedicated Redis database /15.")
    async with Redis.from_url(url) as redis:
        await redis.delete("rate:auth:127.0.0.1", "rate:api:127.0.0.1")
    yield
