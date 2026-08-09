import uuid

import pytest

from app.api.limiter import limiter

pytestmark = pytest.mark.asyncio(loop_scope="session")

SERIALS = "/api/v1/admin/serials"
GENERATE = "/api/v1/admin/serials/generate"
VERIFY = "/api/v1/serials/verify"
PRODUCTS = "/api/v1/admin/products"
ORDERS = "/api/v1/orders"
ADMIN_ORDERS = "/api/v1/admin/orders"
ACCOUNT_ORDERS = "/api/v1/account/me/orders"


async def _place_order(approved_client, admin_client, items):
    r = await approved_client.post(
        ORDERS,
        json={
            "full_name": "Ali Rezaei", "phone": "09121234567",
            "store_name": "Rezaei Jewelry", "province": "Tehran", "items": items,
        },
    )
    assert r.status_code == 201, r.text
    ref = r.json()["reference"]
    listed = (await admin_client.get(ADMIN_ORDERS, params={"q": ref})).json()
    return listed["items"][0]["id"], ref


async def _deliver(admin_client, oid):
    r = await admin_client.patch(f"{ADMIN_ORDERS}/{oid}", json={"status": "delivered"})
    assert r.status_code == 200, r.text
    return r.json()


def _sku():
    return f"SKU-{uuid.uuid4().hex[:8]}"


async def _create_product(admin_client, **over):
    body = {"name": "Vera", "sku": _sku(), "karat": 18, "weight_grams": 4.2, **over}
    r = await admin_client.post(PRODUCTS, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _generate(admin_client, product_id, quantity=1):
    r = await admin_client.post(
        GENERATE, json={"product_id": product_id, "quantity": quantity}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_requires_auth(client):
    assert (await client.get(SERIALS)).status_code == 401


async def test_generate_creates_unique_codes(admin_client):
    p = await _create_product(admin_client)
    rows = await _generate(admin_client, p["id"], quantity=25)
    codes = [r["code"] for r in rows]
    assert len(codes) == 25
    assert len(set(codes)) == 25  # all unique
    assert all(c.startswith("DGV-") for c in codes)


async def test_verify_is_case_and_format_insensitive(admin_client, client):
    p = await _create_product(admin_client, name="Vera Necklace")
    code = (await _generate(admin_client, p["id"]))[0]["code"]  # DGV-XXXXXXXX

    messy = f"  {code.lower().replace('-', ' ')}  "  # "  dgv xxxxxxxx  "
    ok = await client.get(VERIFY, params={"code": messy})
    assert ok.status_code == 200, ok.text
    assert ok.json()["product_name"] == "Vera Necklace"

    assert (await client.get(VERIFY, params={"code": "DGV-ZZZZZZZZ"})).status_code == 404


async def test_revoked_reads_as_not_authentic(admin_client, client):
    p = await _create_product(admin_client)
    row = (await _generate(admin_client, p["id"]))[0]
    assert (await client.get(VERIFY, params={"code": row["code"]})).status_code == 200

    patched = await admin_client.patch(f"{SERIALS}/{row['id']}", json={"status": "revoked"})
    assert patched.status_code == 200
    assert (await client.get(VERIFY, params={"code": row["code"]})).status_code == 404


async def test_verify_survives_product_rename(admin_client, client):
    p = await _create_product(admin_client, name="Original Name")
    code = (await _generate(admin_client, p["id"]))[0]["code"]
    # Rename the product AFTER the serial was minted.
    await admin_client.patch(f"{PRODUCTS}/{p['id']}", json={"name": "Renamed Later"})
    out = await client.get(VERIFY, params={"code": code})
    assert out.status_code == 200
    assert out.json()["product_name"] == "Original Name"  # snapshot, not live


async def test_list_filters_and_prefix_search(admin_client):
    a = await _create_product(admin_client, name="A")
    b = await _create_product(admin_client, name="B")
    await _generate(admin_client, a["id"], quantity=3)
    b_rows = await _generate(admin_client, b["id"], quantity=2)

    by_product = (await admin_client.get(SERIALS, params={"product_id": a["id"]})).json()
    assert by_product["total"] == 3

    # Prefix search by the (normalized) code returns that exact serial.
    one = b_rows[0]["code"]  # DGV-XXXXXXXX
    hit = (await admin_client.get(SERIALS, params={"q": one})).json()
    assert hit["total"] == 1 and hit["items"][0]["code"] == one


async def test_verify_count_tracks_scans(admin_client, client):
    p = await _create_product(admin_client)
    row = (await _generate(admin_client, p["id"]))[0]
    await client.get(VERIFY, params={"code": row["code"]})
    await client.get(VERIFY, params={"code": row["code"]})
    listed = (await admin_client.get(SERIALS, params={"product_id": p["id"]})).json()
    assert listed["items"][0]["verify_count"] == 2


async def test_generate_unknown_product_404(admin_client):
    r = await admin_client.post(
        GENERATE, json={"product_id": str(uuid.uuid4()), "quantity": 1}
    )
    assert r.status_code == 404


async def test_export_csv(admin_client):
    p = await _create_product(admin_client)
    await _generate(admin_client, p["id"], quantity=2)
    r = await admin_client.get(f"{SERIALS}/export", params={"product_id": p["id"]})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "DGV-" in r.text


async def test_delivery_mints_one_serial_per_unit(approved_client, admin_client):
    p = await _create_product(admin_client)
    oid, ref = await _place_order(approved_client, admin_client, [{"product_id": p["id"], "quantity": 3}])
    detail = await _deliver(admin_client, oid)
    assert len(detail["serial_codes"]) == 3
    listed = (await admin_client.get(SERIALS, params={"order_id": oid})).json()
    assert listed["total"] == 3
    assert all(s["status"] == "sold" and s["order_reference"] == ref for s in listed["items"])


async def test_delivery_skips_custom_items(approved_client, admin_client):
    p = await _create_product(admin_client)
    oid, _ = await _place_order(
        approved_client, admin_client,
        [{"product_id": p["id"], "quantity": 2}, {"quantity": 5}],  # 2nd = custom
    )
    detail = await _deliver(admin_client, oid)
    assert len(detail["serial_codes"]) == 2  # custom item minted nothing


async def test_delivery_is_idempotent(approved_client, admin_client):
    p = await _create_product(admin_client)
    oid, _ = await _place_order(approved_client, admin_client, [{"product_id": p["id"], "quantity": 2}])
    await _deliver(admin_client, oid)
    await admin_client.patch(f"{ADMIN_ORDERS}/{oid}", json={"status": "shipped"})
    detail = await _deliver(admin_client, oid)  # deliver again
    assert len(detail["serial_codes"]) == 2  # not 4


async def test_delivered_code_verifies_publicly(approved_client, admin_client, client):
    p = await _create_product(admin_client, name="Vera Ring")
    oid, _ = await _place_order(approved_client, admin_client, [{"product_id": p["id"], "quantity": 1}])
    code = (await _deliver(admin_client, oid))["serial_codes"][0]
    out = await client.get(VERIFY, params={"code": code})
    assert out.status_code == 200 and out.json()["product_name"] == "Vera Ring"


async def test_customer_sees_serial_codes(approved_client, admin_client):
    p = await _create_product(admin_client)
    oid, ref = await _place_order(approved_client, admin_client, [{"product_id": p["id"], "quantity": 1}])
    await _deliver(admin_client, oid)
    mine = (await approved_client.get(ACCOUNT_ORDERS)).json()
    row = next(o for o in mine if o["reference"] == ref)
    assert len(row["serial_codes"]) == 1


async def test_manual_generate_endpoint(approved_client, admin_client):
    p = await _create_product(admin_client)
    oid, _ = await _place_order(approved_client, admin_client, [{"product_id": p["id"], "quantity": 2}])
    r = await admin_client.post(f"{ADMIN_ORDERS}/{oid}/generate-serials")
    assert r.status_code == 200
    assert len(r.json()["codes"]) == 2


async def test_verify_rate_limited(admin_client, client):
    p = await _create_product(admin_client)
    code = (await _generate(admin_client, p["id"]))[0]["code"]
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    codes = []
    for _ in range(32):
        codes.append((await client.get(VERIFY, params={"code": code})).status_code)
    limiter.enabled = False
    assert codes.count(200) == 30  # 30/minute cap
    assert 429 in codes


# ---- Phase 2: QR labels + passport events ----
QR = "/api/v1/serials/{code}/qr.png"


async def test_qr_png_for_known_code(client, admin_client):
    p = await _create_product(admin_client)
    row = (await _generate(admin_client, p["id"]))[0]
    r = await client.get(QR.format(code=row["code"]))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


async def test_qr_unknown_code_404(client):
    assert (await client.get(QR.format(code="DGV-ZZZZZZZZ"))).status_code == 404


async def test_verify_events_minted_only_for_stock(client, admin_client):
    p = await _create_product(admin_client)
    row = (await _generate(admin_client, p["id"]))[0]
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert [e["type"] for e in out["events"]] == ["minted"]


async def test_delivery_adds_sold_event_to_passport(approved_client, admin_client, client):
    p = await _create_product(admin_client)
    oid, _ = await _place_order(
        approved_client, admin_client, [{"product_id": p["id"], "quantity": 1}]
    )
    code = (await _deliver(admin_client, oid))["serial_codes"][0]
    out = (await client.get(VERIFY, params={"code": code})).json()
    assert [e["type"] for e in out["events"]] == ["minted", "sold"]


async def test_admin_status_change_records_sold_event(client, admin_client):
    p = await _create_product(admin_client)
    row = (await _generate(admin_client, p["id"]))[0]
    r = await admin_client.patch(f"{SERIALS}/{row['id']}", json={"status": "sold"})
    assert r.status_code == 200
    out = (await client.get(VERIFY, params={"code": row["code"]})).json()
    assert [e["type"] for e in out["events"]] == ["minted", "sold"]
