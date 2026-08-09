"""گالری سیار (WO 7.6): hand-off, split, quick sale, return, stock report."""

import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOGIN = "/api/v1/admin/login"
ADMIN_GALLERY = "/api/v1/admin/mobile-gallery"
AGENT_GALLERY = "/api/v1/agent/gallery"
PRODUCTS = "/api/v1/admin/products"
GENERATE = "/api/v1/admin/serials/generate"
VERIFY = "/api/v1/serials/verify"


async def _mk_agent(_sessionmaker, username="galagent"):
    from app.core.security import hash_password
    from app.models.user import User

    async with _sessionmaker() as s:
        u = User(username=username, password_hash=hash_password("agent-pass-99"), role="agent")
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


async def _serial(admin_client, **product_over):
    r = await admin_client.post(
        PRODUCTS,
        json={"name": "Vera", "sku": f"SKU-{uuid.uuid4().hex[:8]}", "karat": 18, **product_over},
    )
    p = r.json()
    return (await admin_client.post(GENERATE, json={"product_id": p["id"], "quantity": 1})).json()[0]


async def _assign(admin_client, agent_id, code, **over):
    return await admin_client.post(
        ADMIN_GALLERY, json={"agent_id": str(agent_id), "code": code, **over}
    )


async def test_assign_and_kind_derivation(admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    sellable = await _serial(admin_client)
    sample = await _serial(admin_client, product_status="sample")

    r1 = await _assign(admin_client, agent.id, sellable["code"])
    assert r1.status_code == 201 and r1.json()["kind"] == "sellable"
    r2 = await _assign(admin_client, agent.id, sample["code"])
    assert r2.status_code == 201 and r2.json()["kind"] == "sample"

    out = (await admin_client.get(ADMIN_GALLERY, params={"agent_id": str(agent.id)})).json()
    assert out["counts"] == {"with_agent": 2, "sample": 1, "sellable": 1, "sold": 0, "returned": 0}


async def test_assign_guards(admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    other = await _mk_agent(_sessionmaker, "galagent2")
    row = await _serial(admin_client)
    # already in a bag → 409 (even for another agent)
    assert (await _assign(admin_client, agent.id, row["code"])).status_code == 201
    assert (await _assign(admin_client, other.id, row["code"])).status_code == 409
    # sold serial → 409
    sold = await _serial(admin_client)
    await admin_client.patch(f"/api/v1/admin/serials/{sold['id']}", json={"status": "sold"})
    assert (await _assign(admin_client, agent.id, sold["code"])).status_code == 409
    # unknown code → 404
    assert (await _assign(admin_client, agent.id, "DGV-ZZZZZZZZ")).status_code == 404


async def test_agent_sees_own_bag_and_quick_sells(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    row = await _serial(admin_client)
    await _assign(admin_client, agent.id, row["code"])

    await client.post(LOGIN, json={"username": "galagent", "password": "agent-pass-99"})
    bag = (await client.get(AGENT_GALLERY)).json()
    assert bag["counts"]["with_agent"] == 1
    item = bag["items"][0]

    r = await client.post(f"{AGENT_GALLERY}/{item['id']}/sell", json={"note": "فروش حضوری"})
    assert r.status_code == 200 and r.json()["status"] == "sold"

    # serial flipped to sold + passport event
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert [e["type"] for e in out["events"]] == ["minted", "sold"]

    bag2 = (await client.get(AGENT_GALLERY)).json()
    assert bag2["counts"]["sold"] == 1 and bag2["counts"]["with_agent"] == 0


async def test_sample_cannot_be_sold(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    row = await _serial(admin_client, product_status="sample")
    await _assign(admin_client, agent.id, row["code"])
    await client.post(LOGIN, json={"username": "galagent", "password": "agent-pass-99"})
    item = (await client.get(AGENT_GALLERY)).json()["items"][0]
    assert (await client.post(f"{AGENT_GALLERY}/{item['id']}/sell", json={})).status_code == 409


async def test_agent_cannot_sell_someone_elses_item(client, admin_client, _sessionmaker):
    owner = await _mk_agent(_sessionmaker, "owner1")
    thief = await _mk_agent(_sessionmaker, "thief1")
    row = await _serial(admin_client)
    r = await _assign(admin_client, owner.id, row["code"])
    item_id = r.json()["id"]
    await client.post(LOGIN, json={"username": "thief1", "password": "agent-pass-99"})
    assert (await client.post(f"{AGENT_GALLERY}/{item_id}/sell", json={})).status_code == 404


async def test_return_then_reassign(admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    row = await _serial(admin_client)
    r = await _assign(admin_client, agent.id, row["code"])
    item_id = r.json()["id"]
    rr = await admin_client.patch(f"{ADMIN_GALLERY}/{item_id}/return")
    assert rr.status_code == 200 and rr.json()["status"] == "returned"
    # returned piece can go out again
    assert (await _assign(admin_client, agent.id, row["code"])).status_code == 201
