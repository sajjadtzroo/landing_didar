"""Test wiring for the API suite.

Runs against a real Postgres (the models are Postgres-specific: native UUID +
enum types), in a dedicated `didar_test` database created on first run and
rebuilt per session. Each test starts from truncated tables.

Point at your DB with TEST_DATABASE_URL; default matches docker-compose's
host mapping (db exposed on 5434).

    cd backend && pip install -r requirements-dev.txt
    TEST_DATABASE_URL=postgresql+asyncpg://didar:didar@localhost:5434/didar_test pytest
"""

import os
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.api.v1.public as public
from app.api.deps import require_admin
from app.api.limiter import limiter

# Import every model so Base.metadata knows all tables before create_all.
from app.core.db import Base, get_db
from app.main import app
from app.models import faq, order, product  # noqa: F401

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://didar:didar@localhost:5434/didar_test",
)

_TABLES = "order_status_log, order_items, orders, products, faqs"


async def _ensure_test_db() -> None:
    """CREATE DATABASE (can't run in a transaction) via the always-present
    `didar` maintenance db."""
    u = urlparse(TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))
    dbname = u.path.lstrip("/")
    conn = await asyncpg.connect(
        host=u.hostname, port=u.port, user=u.username,
        password=u.password, database="didar",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname=$1", dbname
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session")
async def _engine():
    await _ensure_test_db()
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def _sessionmaker(_engine):
    return async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _wire(_engine, _sessionmaker, monkeypatch):
    # Route the app's DB dependency at the test database.
    async def _get_db():
        async with _sessionmaker() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    # Rate limiter off by default (one dedicated test flips it on).
    limiter.enabled = False
    # The post-commit notification task uses the app's own SessionLocal (prod
    # URL), not the test engine — stub it so it never fires during tests.
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(public, "_notify", _noop)
    # Clean slate every test.
    async with _engine.begin() as c:
        await c.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_client():
    # Skip the cookie round-trip for admin-guarded routes; the real login/cookie
    # path is covered separately in test_auth.py.
    app.dependency_overrides[require_admin] = lambda: "admin"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def order_payload():
    def make(**over):
        base = dict(
            full_name="Ali Rezaei",
            phone="09121234567",
            store_name="Rezaei Jewelry",
            province="Tehran",
            items=[{"quantity": 2}],
        )
        base.update(over)
        return base

    return make
