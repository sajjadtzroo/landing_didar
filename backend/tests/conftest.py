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
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.api.v1.public as public
from app.api.deps import require_admin
from app.api.limiter import limiter

# Import every model so Base.metadata knows all tables before create_all.
from app.core.db import Base, get_db
from app.main import app
from app.models import (  # noqa: F401
    customer,
    faq,
    landing,
    order,
    portfolio,
    product,
)

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://didar:didar@localhost:5434/didar_test",
)

_TABLES = (
    "order_status_log, order_items, orders, "
    "landings, portfolios, products, faqs, "
    "favorites, customer_addresses, otp_codes, customers, "
    "mobile_gallery_items, warranties, buyback_requests, agent_visits, agent_retailers, users, audit_log, import_jobs"
)


async def _ensure_test_db() -> None:
    """CREATE DATABASE (can't run in a transaction) via the always-present
    `didar` maintenance db."""
    u = urlparse(TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))
    dbname = u.path.lstrip("/")
    conn = await asyncpg.connect(
        host=u.hostname,
        port=u.port,
        user=u.username,
        password=u.password,
        database="didar",
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
    # Anything that opens its own session (audit middleware) hits the test DB too.
    import app.core.db as _db_mod

    monkeypatch.setattr(_db_mod, "SessionLocal", _sessionmaker)
    # Rate limiter off by default (one dedicated test flips it on).
    limiter.enabled = False

    # The post-commit notification task uses the app's own SessionLocal (prod
    # URL), not the test engine — stub it so it never fires during tests.
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(public, "_notify", _noop)
    # The public read endpoints cache via app.core.cache (in-process dict when no
    # REDIS_URL); clear it so one test's reads don't serve stale data to the next.
    import app.core.cache as _cache_mod

    _cache_mod._local.clear()
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


@pytest_asyncio.fixture
async def super_client():
    """Superadmin-guarded routes (users/audit) without the cookie round-trip."""
    from app.api.deps import require_superadmin

    app.dependency_overrides[require_admin] = lambda: "admin"
    app.dependency_overrides[require_superadmin] = lambda: "admin"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_superadmin, None)


@pytest_asyncio.fixture
async def approved_client(_sessionmaker):
    """A logged-in customer who has been admin-approved (can place orders)."""
    from app.models.customer import Customer, CustomerVerificationStatus

    phone = "09129999999"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/account/otp/request", json={"phone": phone})
        code = r.json()["dev_code"]
        await c.post("/api/v1/account/otp/verify", json={"phone": phone, "code": code})
        async with _sessionmaker() as db:
            cust = (
                await db.execute(select(Customer).where(Customer.phone == phone))
            ).scalar_one()
            cust.verification_status = CustomerVerificationStatus.approved
            await db.commit()
        yield c


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
