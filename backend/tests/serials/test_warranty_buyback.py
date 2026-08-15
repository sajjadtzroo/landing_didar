"""Warranty (WO 7.8) + Buyback (WO 7.9) on the UID passport."""

import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

VERIFY = "/api/v1/serials/verify"
PRODUCTS = "/api/v1/admin/products"
GENERATE = "/api/v1/admin/serials/generate"
SERIALS = "/api/v1/admin/serials"

WHO = {"full_name": "علی خریدار", "phone": "09121234567"}


async def _sold_serial(admin_client, **product_over):
    """A sold serial for a fresh product (defaults: warrantable)."""
    r = await admin_client.post(
        PRODUCTS,
        json={"name": "Vera", "sku": f"SKU-{uuid.uuid4().hex[:8]}", "karat": 18,
              "weight_grams": 4.2, **product_over},
    )
    assert r.status_code == 201, r.text
    p = r.json()
    row = (await admin_client.post(GENERATE, json={"product_id": p["id"], "quantity": 1})).json()[0]
    await admin_client.patch(f"{SERIALS}/{row['id']}", json={"status": "sold"})
    return row


def _w(code):
    return f"/api/v1/serials/{code}/warranty"


def _b(code):
    return f"/api/v1/serials/{code}/buyback"


# ---- warranty ----
async def test_activate_warranty_on_sold_piece(client, admin_client):
    row = await _sold_serial(admin_client)
    r = await client.post(_w(row["code"]), json=WHO)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["active"] is True and body["expires_at"] > body["started_at"]

    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert out["warranty"]["active"] is True
    assert out["warranty_available"] is False
    assert "warranty_activated" in [e["type"] for e in out["events"]]


async def test_warranty_available_flag_before_activation(client, admin_client):
    row = await _sold_serial(admin_client)
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert out["warranty_available"] is True and out["warranty"] is None


async def test_warranty_rejected_for_unsold_piece(client, admin_client):
    r = await admin_client.post(
        PRODUCTS, json={"name": "V", "sku": f"SKU-{uuid.uuid4().hex[:8]}"}
    )
    p = r.json()
    row = (await admin_client.post(GENERATE, json={"product_id": p["id"], "quantity": 1})).json()[0]
    assert (await client.post(_w(row["code"]), json=WHO)).status_code == 409


async def test_warranty_rejected_for_non_warrantable(client, admin_client):
    row = await _sold_serial(admin_client, warrantable=False)
    assert (await client.post(_w(row["code"]), json=WHO)).status_code == 409
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert out["warranty_available"] is False


async def test_warranty_double_activation_409(client, admin_client):
    row = await _sold_serial(admin_client)
    assert (await client.post(_w(row["code"]), json=WHO)).status_code == 201
    assert (await client.post(_w(row["code"]), json=WHO)).status_code == 409


async def test_warranty_unknown_code_404(client):
    assert (await client.post(_w("DGV-ZZZZZZZZ"), json=WHO)).status_code == 404


# ---- buyback ----
async def test_buyback_request_and_status_on_passport(client, admin_client):
    row = await _sold_serial(admin_client)
    r = await client.post(_b(row["code"]), json={**WHO, "note": "می‌خواهم بفروشم"})
    assert r.status_code == 201
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert out["buyback_status"] == "under_review"
    assert "buyback_requested" in [e["type"] for e in out["events"]]


async def test_buyback_duplicate_open_request_409(client, admin_client):
    row = await _sold_serial(admin_client)
    assert (await client.post(_b(row["code"]), json=WHO)).status_code == 201
    assert (await client.post(_b(row["code"]), json=WHO)).status_code == 409


async def test_buyback_open_request_unique_enforced_by_db(admin_client, _sessionmaker):
    """The partial unique index (one under_review per serial) must hold even when
    the app-level check is bypassed — that's the concurrent-request backstop."""
    from sqlalchemy.exc import IntegrityError

    from app.domains.serials import BuybackRequest

    row = await _sold_serial(admin_client)
    serial_id = uuid.UUID(row["id"])

    def _req():
        return BuybackRequest(
            serial_id=serial_id, requester_name="علی", requester_phone="09121234567"
        )

    async with _sessionmaker() as db:
        db.add(_req())
        await db.commit()
        db.add(_req())
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_admin_processes_buyback(client, admin_client):
    row = await _sold_serial(admin_client)
    await client.post(_b(row["code"]), json=WHO)
    listed = (await admin_client.get("/api/v1/admin/buybacks")).json()
    assert listed["total"] == 1
    b = listed["items"][0]
    assert b["code"] == row["code"] and b["status"] == "under_review"

    r = await admin_client.patch(
        f"/api/v1/admin/buybacks/{b['id']}",
        json={"status": "accepted", "offered_price": 250000000, "admin_note": "تأیید شد"},
    )
    assert r.status_code == 200 and r.json()["status"] == "accepted"

    # accepted → the piece can take a new request
    assert (await client.post(_b(row["code"]), json=WHO)).status_code == 201

    # public passport shows latest status, never the price
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert out["buyback_status"] == "under_review"
    assert "offered_price" not in out


async def test_buyback_export_csv(client, admin_client):
    row = await _sold_serial(admin_client)
    await client.post(_b(row["code"]), json=WHO)
    r = await admin_client.get("/api/v1/admin/buybacks/export")
    assert r.status_code == 200
    assert row["code"] in r.text and "under_review" in r.text


async def test_buyback_rejected_for_unsold_piece(client, admin_client):
    """Review fix: an in-stock (undelivered) piece can't take a buyback request."""
    r = await admin_client.post(
        PRODUCTS, json={"name": "V", "sku": f"SKU-{uuid.uuid4().hex[:8]}"}
    )
    row = (
        await admin_client.post(GENERATE, json={"product_id": r.json()["id"], "quantity": 1})
    ).json()[0]
    assert (await client.post(_b(row["code"]), json=WHO)).status_code == 409
