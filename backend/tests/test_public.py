import uuid
from decimal import Decimal

import pytest

import app.core.db as _db_mod
from app.core.limiter import limiter
from app.domains.content import Landing
from app.domains.content import service as _content_service
from app.domains.orders.routers import public as _orders_public

pytestmark = pytest.mark.asyncio(loop_scope="session")

ORDERS = "/api/v1/orders"

# Grab the real _notify at import time — conftest's autouse fixture stubs the
# module attribute during every test, so this is the only handle to the original.
_REAL_NOTIFY = _orders_public._notify


async def _make_product(admin_client, **over):
    body = {"name": "Ring", "sku": f"R-{uuid.uuid4().hex[:8]}", **over}
    r = await admin_client.post("/api/v1/admin/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---- GET /products ----
async def test_list_products_empty(client):
    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_products_hides_inactive_and_sorts(client, admin_client):
    await _make_product(admin_client, name="B", sort_order=2)
    await _make_product(admin_client, name="A", sort_order=1)
    await _make_product(admin_client, name="Hidden", is_active=False)

    r = await client.get("/api/v1/products")
    names = [p["name"] for p in r.json()]
    assert names == ["A", "B"]  # inactive excluded, sorted by sort_order


async def test_list_products_excludes_not_for_sale_keeps_sample(client, admin_client):
    await _make_product(admin_client, name="Sellable", sort_order=1)
    await _make_product(admin_client, name="Sample", product_status="sample", sort_order=2)
    await _make_product(
        admin_client, name="Hidden", product_status="not_for_sale", sort_order=3
    )
    names = [p["name"] for p in (await client.get("/api/v1/products")).json()]
    assert names == ["Sellable", "Sample"]  # not_for_sale hidden, sample kept


async def test_not_for_sale_slug_404_but_sample_reachable(client, admin_client):
    await _make_product(
        admin_client, name="S", slug="sample-ring", product_status="sample"
    )
    await _make_product(
        admin_client, name="N", slug="nfs-ring", product_status="not_for_sale"
    )
    assert (await client.get("/api/v1/products/sample-ring")).status_code == 200
    assert (await client.get("/api/v1/products/nfs-ring")).status_code == 404


# ---- GET /products/{slug} ----
async def test_get_product_by_slug(client, admin_client):
    p = await _make_product(admin_client, name="Nova", slug="nova-ring")
    r = await client.get("/api/v1/products/nova-ring")
    assert r.status_code == 200
    assert r.json()["id"] == p["id"]


async def test_get_product_unknown_slug_404(client):
    r = await client.get("/api/v1/products/does-not-exist")
    assert r.status_code == 404


async def test_get_product_inactive_slug_404(client, admin_client):
    await _make_product(admin_client, name="Ghost", slug="ghost-ring", is_active=False)
    r = await client.get("/api/v1/products/ghost-ring")
    assert r.status_code == 404  # inactive products are not publicly reachable


# ---- GET /faqs ----
async def test_list_faqs_hides_inactive(client, admin_client):
    await admin_client.post(
        "/api/v1/admin/faqs", json={"question": "Q1", "answer": "A1"}
    )
    await admin_client.post(
        "/api/v1/admin/faqs",
        json={"question": "Q2", "answer": "A2", "is_active": False},
    )
    r = await client.get("/api/v1/faqs")
    assert [f["question"] for f in r.json()] == ["Q1"]


# ---- POST /orders ----
async def test_create_order_custom_item(approved_client, order_payload):
    r = await approved_client.post(ORDERS, json=order_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reference"].startswith("DG-")
    assert Decimal(body["total"]) == 0  # no product_id => "custom item", no weight


async def test_create_order_totals_grams_from_product(
    approved_client, admin_client, order_payload
):
    p = await _make_product(admin_client, weight_grams=100)
    r = await approved_client.post(
        ORDERS,
        json=order_payload(items=[{"product_id": p["id"], "quantity": 3}]),
    )
    assert r.status_code == 201
    assert Decimal(r.json()["total"]) == 300  # server-trusted weight(g) * qty


async def test_honeypot_returns_fake_and_persists_nothing(
    approved_client, admin_client, order_payload
):
    r = await approved_client.post(ORDERS, json=order_payload(website="spam"))
    assert r.status_code == 201
    assert r.json() == {"reference": "DG-000000", "total": "0"}
    # nothing stored
    listed = await admin_client.get("/api/v1/admin/orders")
    assert listed.json()["total"] == 0


async def test_idempotency_key_dedupes(approved_client, admin_client, order_payload):
    hdr = {"Idempotency-Key": str(uuid.uuid4())}
    r1 = await approved_client.post(ORDERS, json=order_payload(), headers=hdr)
    r2 = await approved_client.post(ORDERS, json=order_payload(), headers=hdr)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["reference"] == r2.json()["reference"]
    listed = await admin_client.get("/api/v1/admin/orders")
    assert listed.json()["total"] == 1  # only one row


@pytest.mark.parametrize(
    "override",
    [
        {"phone": "0912"},  # bad phone
        {"province": "Atlantis"},  # not an Iran province
        {"items": []},  # needs >= 1 item
        {"full_name": "Al"},  # too short
    ],
)
async def test_create_order_validation(approved_client, order_payload, override):
    r = await approved_client.post(ORDERS, json=order_payload(**override))
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body and "field" in body  # consistent error envelope


# ---- GET /orders/track ----
TRACK = "/api/v1/orders/track"


async def test_track_order_matches_reference_and_phone(
    approved_client, admin_client, order_payload
):
    p = await _make_product(admin_client, weight_grams=100)
    ref = (
        await approved_client.post(
            ORDERS,
            json=order_payload(items=[{"product_id": p["id"], "quantity": 2}]),
        )
    ).json()["reference"]

    # phone is bound from the approved session (09129999999), not the payload
    r = await approved_client.get(
        TRACK, params={"reference": ref, "phone": "09129999999"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reference"] == ref
    assert body["status"] == "new"
    assert Decimal(body["total"]) == 200
    assert len(body["items"]) == 1
    assert body["status_log"][0]["to_status"] == "new"


async def test_track_order_wrong_phone_is_404(approved_client, client, order_payload):
    ref = (await approved_client.post(ORDERS, json=order_payload())).json()["reference"]
    r = await client.get(TRACK, params={"reference": ref, "phone": "09120000000"})
    assert r.status_code == 404  # right ref, wrong phone => same 404 (no enumeration)


async def test_track_order_unknown_reference_is_404(client):
    r = await client.get(
        TRACK, params={"reference": "DG-ZZZZZZ", "phone": "09121234567"}
    )
    assert r.status_code == 404


async def test_rate_limit_after_five(approved_client, order_payload):
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001 — older slowapi has no reset(); storage is fresh
        pass
    codes = []
    for _ in range(6):
        codes.append(
            (await approved_client.post(ORDERS, json=order_payload())).status_code
        )
    limiter.enabled = False
    assert codes.count(201) == 5
    assert codes[-1] == 429


# ---- In-process TTL cache (hit branch) ----
async def test_products_served_from_cache_within_ttl(client, admin_client):
    await _make_product(admin_client, name="A")
    assert [p["name"] for p in (await client.get("/api/v1/products")).json()] == ["A"]
    # Add B AFTER the first read populated the cache; the cached payload wins.
    await _make_product(admin_client, name="B")
    assert [p["name"] for p in (await client.get("/api/v1/products")).json()] == ["A"]


async def test_faqs_served_from_cache_within_ttl(client, admin_client):
    await admin_client.post("/api/v1/admin/faqs", json={"question": "Q1", "answer": "A1"})
    assert len((await client.get("/api/v1/faqs")).json()) == 1
    await admin_client.post("/api/v1/admin/faqs", json={"question": "Q2", "answer": "A2"})
    assert len((await client.get("/api/v1/faqs")).json()) == 1  # cached, Q2 hidden


# ---- Landing content → resolved product groups ----
async def _insert_landing(_sessionmaker, slug, content):
    async with _sessionmaker() as s:
        s.add(Landing(slug=slug, title="LX", content=content))
        await s.commit()


async def test_landing_groups_resolve_and_drop_inactive_or_bad_ids(
    client, admin_client, _sessionmaker
):
    active = await _make_product(admin_client, name="Live")
    inactive = await _make_product(admin_client, name="Dead", is_active=False)
    content = {
        "groups": [
            {
                "title": "G",
                "eyebrow": "E",
                "description": "D",
                # valid+active, valid+inactive (dropped), and a non-uuid (dropped)
                "product_ids": [active["id"], inactive["id"], "not-a-uuid"],
            }
        ]
    }
    await _insert_landing(_sessionmaker, "lx", content)

    r = await client.get("/api/v1/landings/lx")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "lx"
    groups = body["groups"]
    assert len(groups) == 1 and groups[0]["title"] == "G"
    assert [p["name"] for p in groups[0]["products"]] == ["Live"]  # only active kept

    # Second GET is served from cache (landing:lx) — still 200 with same payload.
    assert (await client.get("/api/v1/landings/lx")).json()["groups"][0]["products"]


async def test_get_landing_unknown_slug_is_404(client):
    assert (await client.get("/api/v1/landings/does-not-exist")).status_code == 404


async def test_bust_landing_cache_drops_entry(_sessionmaker):
    from app.core.cache import cache_get, cache_set

    await cache_set("cache:landing:z", "cached", ttl=999)
    await _content_service.bust_landing_cache("z")
    assert await cache_get("cache:landing:z") is None


async def test_landing_null_content_falls_back_to_defaults(client, _sessionmaker):
    await _insert_landing(_sessionmaker, "blank", None)
    body = (await client.get("/api/v1/landings/blank")).json()
    assert body["slug"] == "blank"
    assert body["groups"] == []  # default_content has no product groups
    assert body["content"]["hero"]["headline"]  # default hero present


# ---- Background notification task (the real _notify, mocked deps) ----
class _FakeSession:
    def __init__(self, order):
        self._order = order

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, model, oid):
        return self._order


class _Adapter:
    def __init__(self, fail=False):
        self.calls = 0
        self._fail = fail

    async def send_new_order(self, order, admin_url):
        self.calls += 1
        if self._fail:
            raise RuntimeError("transport down")


async def _run_notify(monkeypatch, order, adapter):
    monkeypatch.setattr(_db_mod, "SessionLocal", lambda: _FakeSession(order))
    monkeypatch.setattr(_orders_public, "get_adapter", lambda: adapter)
    await _REAL_NOTIFY("order-id", "http://x/admin/orders")


async def test_notify_missing_order_does_not_call_adapter(monkeypatch):
    adapter = _Adapter()
    await _run_notify(monkeypatch, None, adapter)  # db.get returns None
    assert adapter.calls == 0


async def test_notify_sends_once_on_success(monkeypatch):
    adapter = _Adapter()
    await _run_notify(monkeypatch, object(), adapter)
    assert adapter.calls == 1  # returns after the first successful send


async def test_notify_retries_once_then_gives_up_without_raising(monkeypatch):
    adapter = _Adapter(fail=True)
    await _run_notify(monkeypatch, object(), adapter)  # must not raise
    assert adapter.calls == 2  # two attempts, both logged, swallowed
