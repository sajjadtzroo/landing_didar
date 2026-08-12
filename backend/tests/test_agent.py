"""Agent field sales (WO 7.5): assignment scoping, order-on-behalf, delivery."""

import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOGIN = "/api/v1/admin/login"
RETAILERS = "/api/v1/agent/retailers"
AGENT_ORDERS = "/api/v1/agent/orders"
VISITS = "/api/v1/agent/visits"
PRODUCTS = "/api/v1/admin/products"


async def _mk_agent(_sessionmaker, username="agent1", password="agent-pass-99"):
    from app.core.security import hash_password
    from app.domains.users import User

    async with _sessionmaker() as s:
        u = User(
            username=username,
            password_hash=hash_password(password),
            full_name="ایجنت نمونه",
            role="agent",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


async def _mk_retailer(_sessionmaker, phone="09121110000", store="طلای شرق"):
    from app.domains.customers import Customer, CustomerVerificationStatus

    async with _sessionmaker() as s:
        c = Customer(
            phone=phone,
            store_name=store,
            full_name="مالک فروشگاه",
            verification_status=CustomerVerificationStatus.approved,
        )
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c


async def _assign(_sessionmaker, agent_id, customer_id):
    from app.models.agent import AgentRetailer

    async with _sessionmaker() as s:
        s.add(AgentRetailer(agent_id=agent_id, customer_id=customer_id))
        await s.commit()


async def _agent_login(client, username="agent1", password="agent-pass-99"):
    r = await client.post(LOGIN, json={"username": username, "password": password})
    assert r.status_code == 200, r.text


async def _mk_product(admin_client, weight=5):
    r = await admin_client.post(
        PRODUCTS,
        json={"name": "Vera", "sku": f"SKU-{uuid.uuid4().hex[:8]}", "weight_grams": weight, "karat": 18},
    )
    assert r.status_code == 201
    return r.json()


async def test_agent_endpoints_require_agent_role(client, _sessionmaker):
    from app.core.security import hash_password
    from app.domains.users import User

    async with _sessionmaker() as s:
        s.add(User(username="op9", password_hash=hash_password("operator-pass"), role="operator"))
        await s.commit()
    await _agent_login(client, "op9", "operator-pass")
    assert (await client.get(RETAILERS)).status_code == 403


async def test_agent_sees_only_assigned_retailers(client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    mine = await _mk_retailer(_sessionmaker, phone="09121110001", store="فروشگاه من")
    await _mk_retailer(_sessionmaker, phone="09121110002", store="فروشگاه دیگری")
    await _assign(_sessionmaker, agent.id, mine.id)

    await _agent_login(client)
    rows = (await client.get(RETAILERS)).json()
    assert [r["store_name"] for r in rows] == ["فروشگاه من"]


async def test_order_on_behalf_sets_agent_and_totals(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client, weight=5)

    await _agent_login(client)
    r = await client.post(
        AGENT_ORDERS,
        json={
            "customer_id": str(retailer.id),
            "province": "Tehran",
            "items": [{"product_id": p["id"], "quantity": 3}],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["agent_username"] == "agent1"
    assert float(body["total"]) == 15  # 5g × 3, server-trusted
    assert body["store_name"] == "طلای شرق"


async def test_order_for_unassigned_retailer_404(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    other = await _mk_retailer(_sessionmaker, phone="09121110003")
    p = await _mk_product(admin_client)
    await _agent_login(client)
    r = await client.post(
        AGENT_ORDERS,
        json={
            "customer_id": str(other.id),
            "province": "Tehran",
            "items": [{"product_id": p["id"], "quantity": 1}],
        },
    )
    assert r.status_code == 404


async def test_my_orders_scoped_to_agent(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client)
    await _agent_login(client)
    await client.post(
        AGENT_ORDERS,
        json={"customer_id": str(retailer.id), "province": "Tehran",
              "items": [{"product_id": p["id"], "quantity": 1}]},
    )
    mine = (await client.get(AGENT_ORDERS)).json()
    assert len(mine) == 1 and mine[0]["agent_username"] == "agent1"


async def test_agent_delivery_mints_serials_with_proof(client, admin_client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client)
    await _agent_login(client)
    oid = (
        await client.post(
            AGENT_ORDERS,
            json={"customer_id": str(retailer.id), "province": "Tehran",
                  "items": [{"product_id": p["id"], "quantity": 2}]},
        )
    ).json()["id"]
    r = await client.post(f"{AGENT_ORDERS}/{oid}/deliver", json={"note": "تحویل شد"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "delivered"
    assert len(body["serial_codes"]) == 2
    assert body["delivered_at"] is not None


async def test_visits_scoped_and_validated(client, _sessionmaker):
    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    await _agent_login(client)
    r = await client.post(
        VISITS, json={"customer_id": str(retailer.id), "note": "ویترین بررسی شد"}
    )
    assert r.status_code == 201
    rows = (await client.get(VISITS, params={"customer_id": str(retailer.id)})).json()
    assert len(rows) == 1 and rows[0]["note"] == "ویترین بررسی شد"


async def test_preparing_status_accepted(admin_client, approved_client):
    r = await approved_client.post(
        "/api/v1/orders",
        json={"full_name": "Ali Rezaei", "phone": "09121234567",
              "store_name": "Rezaei", "province": "Tehran",
              "items": [{"quantity": 1}]},
    )
    assert r.status_code == 201
    ref = r.json()["reference"]
    oid = (await admin_client.get("/api/v1/admin/orders", params={"q": ref})).json()["items"][0]["id"]
    pr = await admin_client.patch(f"/api/v1/admin/orders/{oid}", json={"status": "preparing"})
    assert pr.status_code == 200 and pr.json()["status"] == "preparing"


async def test_agent_orders_hide_admin_fields(client, admin_client, _sessionmaker):
    """Review fix: internal_note / is_read / attribution never reach agents."""
    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client)
    await _agent_login(client)
    created = (
        await client.post(
            AGENT_ORDERS,
            json={"customer_id": str(retailer.id), "province": "Tehran",
                  "items": [{"product_id": p["id"], "quantity": 1}]},
        )
    ).json()
    listed = (await client.get(AGENT_ORDERS)).json()[0]
    for payload in (created, listed):
        for hidden in ("internal_note", "is_read", "utm_source", "referrer", "phone"):
            assert hidden not in payload, hidden


async def test_superadmin_can_deliver_agent_order(client, admin_client, _sessionmaker):
    """Review fix: the oversight path — superadmin delivers any agent order."""
    from app.core.security import hash_password
    from app.domains.users import User

    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client)
    await _agent_login(client)
    oid = (
        await client.post(
            AGENT_ORDERS,
            json={"customer_id": str(retailer.id), "province": "Tehran",
                  "items": [{"product_id": p["id"], "quantity": 1}]},
        )
    ).json()["id"]
    async with _sessionmaker() as s:
        s.add(User(username="boss", password_hash=hash_password("boss-pass-99"), role="superadmin"))
        await s.commit()
    await _agent_login(client, "boss", "boss-pass-99")
    r = await client.post(f"{AGENT_ORDERS}/{oid}/deliver", json={"note": "بازرسی"})
    assert r.status_code == 200 and r.json()["status"] == "delivered"


async def test_agent_mutations_are_audited(client, admin_client, _sessionmaker):
    """Review fix: agent order placement/delivery land in the audit trail."""
    from sqlalchemy import select

    from app.domains.users import AuditLog

    agent = await _mk_agent(_sessionmaker)
    retailer = await _mk_retailer(_sessionmaker)
    await _assign(_sessionmaker, agent.id, retailer.id)
    p = await _mk_product(admin_client)
    await _agent_login(client)
    await client.post(
        AGENT_ORDERS,
        json={"customer_id": str(retailer.id), "province": "Tehran",
              "items": [{"product_id": p["id"], "quantity": 1}]},
    )
    async with _sessionmaker() as s:
        rows = (await s.execute(select(AuditLog))).scalars().all()
    assert ("agent1", "POST /api/v1/agent/orders") in [(a.actor, a.action) for a in rows]
