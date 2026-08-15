"""Unit tests for app.core.cache — the dict backend, the (faked) Redis code path,
and the fail-open circuit breaker. No real Redis needed; an env-gated e2e against a
real server lives at the bottom (REDIS_TEST_URL), mirroring the MinIO e2e pattern."""

import os
import uuid

import pytest
from pydantic import BaseModel

import app.core.cache as cache
from app.core.config import settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def _fresh():
    cache.clear_all()
    cache._down_until = 0.0
    yield
    cache.clear_all()
    cache._down_until = 0.0
    cache._redis = None


# ---- dict backend (REDIS_URL unset — the default everywhere in tests) ----
async def test_dict_roundtrip_and_delete():
    await cache.cache_set("cache:x", {"a": 1}, ttl=60)
    assert await cache.cache_get("cache:x") == {"a": 1}
    await cache.cache_delete("cache:x")
    assert await cache.cache_get("cache:x") is None


async def test_dict_ttl_expires(monkeypatch):
    await cache.cache_set("cache:x", "v", ttl=60)
    real = cache.time.monotonic
    monkeypatch.setattr(cache.time, "monotonic", lambda: real() + 61)
    assert await cache.cache_get("cache:x") is None


async def test_values_are_json_shapes_for_both_backends():
    class M(BaseModel):
        id: uuid.UUID
        name: str

    m = M(id=uuid.uuid4(), name="ring")
    await cache.cache_set("cache:m", [m], ttl=60)
    got = await cache.cache_get("cache:m")
    # jsonable_encoder normalizes: same shape a Redis JSON roundtrip would give.
    assert got == [{"id": str(m.id), "name": "ring"}]


# ---- redis code path via a hand-rolled fake ----
class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.ttls[key] = ex

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


class _BrokenRedis:
    async def get(self, key):
        raise ConnectionError("redis down")

    async def set(self, *a, **k):
        raise ConnectionError("redis down")

    async def delete(self, *a):
        raise ConnectionError("redis down")


@pytest.fixture
def _redis_backend(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(settings, "redis_url", "redis://fake:6379/0")
    monkeypatch.setattr(cache, "_redis", fake)
    return fake


async def test_redis_roundtrip_serializes_json(_redis_backend):
    await cache.cache_set("cache:x", {"n": 5}, ttl=90)
    assert _redis_backend.ttls["cache:x"] == 90  # TTL passed through as EX
    assert isinstance(_redis_backend.store["cache:x"], str)  # stored as JSON text
    assert await cache.cache_get("cache:x") == {"n": 5}
    await cache.cache_delete("cache:x")
    assert "cache:x" not in _redis_backend.store


async def test_redis_failure_fails_open_and_backs_off(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://fake:6379/0")
    monkeypatch.setattr(cache, "_redis", _BrokenRedis())

    assert await cache.cache_get("cache:x") is None  # error => miss, no raise
    assert cache._down_until > cache.time.monotonic()  # breaker armed

    # While backing off, calls use the local dict instead of touching Redis.
    await cache.cache_set("cache:x", "v", ttl=60)
    assert await cache.cache_get("cache:x") == "v"


# ---- env-gated e2e against a REAL redis (e.g. the compose service) ----
_REAL = os.getenv("REDIS_TEST_URL")


@pytest.mark.skipif(not _REAL, reason="set REDIS_TEST_URL to run the Redis e2e")
async def test_real_redis_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", _REAL)
    monkeypatch.setattr(cache, "_redis", None)  # force a real client from the URL
    key = f"cache:test:{uuid.uuid4().hex}"
    await cache.cache_set(key, {"hello": "دیدار"}, ttl=30)
    assert await cache.cache_get(key) == {"hello": "دیدار"}
    await cache.cache_delete(key)
    assert await cache.cache_get(key) is None
