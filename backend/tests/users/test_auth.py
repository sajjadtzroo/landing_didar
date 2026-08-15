"""Real login -> signed cookie -> /me flow (require_admin NOT overridden here)."""

import pytest

from app.core.config import settings
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOGIN = "/api/v1/admin/login"
LOGOUT = "/api/v1/admin/logout"
ME = "/api/v1/admin/me"


@pytest.fixture(autouse=True)
def _admin_creds(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password_hash", hash_password("secret123"))


async def test_login_success_sets_cookie(client):
    r = await client.post(LOGIN, json={"username": "admin", "password": "secret123"})
    assert r.status_code == 200
    assert r.json() == {"username": "admin", "role": "superadmin"}
    assert "didar_admin" in r.cookies


async def test_login_bad_password(client):
    r = await client.post(LOGIN, json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    assert (await client.get(ME)).status_code == 401


async def test_me_after_login(client):
    await client.post(LOGIN, json={"username": "admin", "password": "secret123"})
    r = await client.get(ME)  # cookie carried by the client
    assert r.status_code == 200
    assert r.json() == {"username": "admin", "role": "superadmin"}


async def test_logout_clears_session(client):
    await client.post(LOGIN, json={"username": "admin", "password": "secret123"})
    assert (await client.post(LOGOUT)).status_code == 200
    assert (await client.get(ME)).status_code == 401  # cleared cookie => no session


async def test_login_rate_limited(client):
    """Brute-force guard: the 11th attempt in a minute is 429."""
    from app.core.limiter import limiter

    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001 — older slowapi lacks reset()
        pass
    codes = [
        (await client.post(LOGIN, json={"username": "admin", "password": "wrong!!!"})).status_code
        for _ in range(11)
    ]
    limiter.enabled = False
    assert codes[-1] == 429 and codes[0] == 401
