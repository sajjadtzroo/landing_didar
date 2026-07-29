import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

ORDERS = "/api/v1/admin/orders"


async def _create_order(client, order_payload, **over):
    r = await client.post("/api/v1/orders", json=order_payload(**over))
    assert r.status_code == 201, r.text
    return r.json()["reference"]


async def _first_order(admin_client):
    r = await admin_client.get(ORDERS)
    return r.json()["items"][0]


async def test_requires_auth(client):
    assert (await client.get(ORDERS)).status_code == 401


async def test_list_empty(admin_client):
    r = await admin_client.get(ORDERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0 and body["items"] == [] and body["unread"] == 0


async def test_list_counts_unread(client, admin_client, order_payload):
    await _create_order(client, order_payload)
    body = (await admin_client.get(ORDERS)).json()
    assert body["total"] == 1
    assert body["unread"] == 1  # is_read defaults False


async def test_filter_by_status(client, admin_client, order_payload):
    await _create_order(client, order_payload)
    confirmed = await admin_client.get(ORDERS, params={"status": "confirmed"})
    assert confirmed.json()["total"] == 0
    new = await admin_client.get(ORDERS, params={"status": "new"})
    assert new.json()["total"] == 1


async def test_search_query(client, admin_client, order_payload):
    await _create_order(client, order_payload, full_name="Zahra Test")
    hit = (await admin_client.get(ORDERS, params={"q": "Zahra"})).json()
    assert hit["total"] == 1
    miss = (await admin_client.get(ORDERS, params={"q": "Nobody"})).json()
    assert miss["total"] == 0


async def test_pagination(client, admin_client, order_payload):
    for _ in range(3):
        await _create_order(client, order_payload)
    page = (await admin_client.get(ORDERS, params={"page_size": 2, "page": 1})).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2


async def test_get_order_404(admin_client):
    r = await admin_client.get(f"{ORDERS}/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_get_order_detail(client, admin_client, order_payload):
    await _create_order(client, order_payload)
    order = await _first_order(admin_client)
    r = await admin_client.get(f"{ORDERS}/{order['id']}")
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["items"]) == 1
    assert detail["status_log"][0]["to_status"] == "new"  # initial log entry


async def test_patch_status_note_and_read(client, admin_client, order_payload):
    await _create_order(client, order_payload)
    order = await _first_order(admin_client)
    r = await admin_client.patch(
        f"{ORDERS}/{order['id']}",
        json={"status": "contacted", "internal_note": "called back", "is_read": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "contacted"
    assert body["internal_note"] == "called back"
    assert body["is_read"] is True
    # a status change appends to the log
    assert [e["to_status"] for e in body["status_log"]] == ["new", "contacted"]


async def test_export_csv(client, admin_client, order_payload):
    ref = await _create_order(client, order_payload)
    r = await admin_client.get(f"{ORDERS}/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "reference" in r.text  # header row
    assert ref in r.text
