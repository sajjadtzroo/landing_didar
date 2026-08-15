"""RBAC + audit (WO 7.15): named users with roles, env-admin bootstrap, and the
audit trail middleware."""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOGIN = "/api/v1/admin/login"
ME = "/api/v1/admin/me"
USERS = "/api/v1/admin/users"
AUDIT = "/api/v1/admin/audit"
FAQS = "/api/v1/admin/faqs"


async def _login(client, username, password):
    return await client.post(LOGIN, json={"username": username, "password": password})


@pytest.fixture(autouse=True)
def _env_admin(monkeypatch):
    from app.core.config import settings
    from app.core.security import hash_password

    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password_hash", hash_password("admin-pass"))


async def _login_env_admin(client):
    r = await _login(client, "admin", "admin-pass")
    assert r.status_code == 200, r.text
    return r


async def _insert_user(_sessionmaker, username, role, password="secret-123"):
    from app.core.security import hash_password
    from app.domains.users import User

    async with _sessionmaker() as s:
        u = User(username=username, password_hash=hash_password(password), role=role)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


# ---- login + roles ----
async def test_env_admin_still_logs_in_as_superadmin(client):
    r = await _login_env_admin(client)
    assert r.json() == {"username": "admin", "role": "superadmin"}
    me = await client.get(ME)
    assert me.json()["role"] == "superadmin"


async def test_db_user_login_and_role(client, _sessionmaker):
    await _insert_user(_sessionmaker, "op1", "operator")
    r = await _login(client, "op1", "secret-123")
    assert r.status_code == 200 and r.json()["role"] == "operator"


async def test_wrong_password_401(client, _sessionmaker):
    await _insert_user(_sessionmaker, "op2", "operator")
    assert (await _login(client, "op2", "wrong-password")).status_code == 401


async def test_operator_uses_panel_but_not_user_management(client, _sessionmaker):
    await _insert_user(_sessionmaker, "op3", "operator")
    await _login(client, "op3", "secret-123")
    assert (await client.get("/api/v1/admin/orders")).status_code == 200
    assert (await client.get(USERS)).status_code == 403
    assert (await client.get(AUDIT)).status_code == 403


async def test_agent_role_has_no_panel_access(client, _sessionmaker):
    await _insert_user(_sessionmaker, "agent1", "agent")
    await _login(client, "agent1", "secret-123")
    assert (await client.get("/api/v1/admin/orders")).status_code == 403


async def test_deactivated_user_locked_out_immediately(client, _sessionmaker):
    u = await _insert_user(_sessionmaker, "op4", "operator")
    await _login(client, "op4", "secret-123")
    assert (await client.get(ME)).status_code == 200
    from sqlalchemy import update

    from app.domains.users import User

    async with _sessionmaker() as s:
        await s.execute(update(User).where(User.id == u.id).values(is_active=False))
        await s.commit()
    assert (await client.get(ME)).status_code == 401  # same session, now dead


async def test_duplicate_username_409(super_client):
    r1 = await super_client.post(
        USERS, json={"username": "dup", "password": "secret-123", "role": "operator"}
    )
    assert r1.status_code == 201
    r = await super_client.post(
        USERS, json={"username": "dup", "password": "secret-123", "role": "operator"}
    )
    assert r.status_code == 409


async def test_cannot_delete_or_deactivate_yourself(client, _sessionmaker):
    await _insert_user(_sessionmaker, "root2", "superadmin")
    await _login(client, "root2", "secret-123")
    uid = next(
        u["id"] for u in (await client.get(USERS)).json() if u["username"] == "root2"
    )
    assert (await client.delete(f"{USERS}/{uid}")).status_code == 400
    r = await client.patch(f"{USERS}/{uid}", json={"is_active": False})
    assert r.status_code == 400


# ---- audit trail ----
async def test_mutations_and_logins_are_audited(client):
    await _login_env_admin(client)
    # a mutating admin call through the real cookie path
    r = await client.post(FAQS, json={"question": "Q", "answer": "A"})
    assert r.status_code == 201
    audit = (await client.get(AUDIT)).json()
    actions = [(a["actor"], a["action"]) for a in audit["items"]]
    assert ("admin", "POST /api/v1/admin/faqs") in actions
    assert ("admin", "auth.login") in actions


async def test_failed_login_is_audited(client):
    await _login(client, "ghost", "nope-nope-nope")
    await _login_env_admin(client)
    rows = (await client.get(AUDIT, params={"actor": "ghost"})).json()
    assert rows["total"] == 1 and rows["items"][0]["status"] == 401
