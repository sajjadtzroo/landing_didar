import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

PRODUCTS = "/api/v1/admin/products"
FAQS = "/api/v1/admin/faqs"


def _sku():
    return f"SKU-{uuid.uuid4().hex[:8]}"


async def test_requires_auth(client):
    assert (await client.get(PRODUCTS)).status_code == 401
    assert (await client.get(FAQS)).status_code == 401


# ---- Products ----
async def test_ojrat_percent_roundtrips_and_validates(admin_client):
    created = await admin_client.post(
        PRODUCTS, json={"name": "Ring", "sku": _sku(), "ojrat_percent": 7}
    )
    assert created.status_code == 201
    assert created.json()["ojrat_percent"] == "7.00"  # Decimal(5,2) serialized
    # out of the 0–100 range is rejected
    bad = await admin_client.post(
        PRODUCTS, json={"name": "Ring", "sku": _sku(), "ojrat_percent": 150}
    )
    assert bad.status_code == 422


async def test_product_crud(admin_client):
    body = {"name": "Bracelet", "sku": _sku()}
    created = await admin_client.post(PRODUCTS, json=body)
    assert created.status_code == 201
    pid = created.json()["id"]

    assert len((await admin_client.get(PRODUCTS)).json()) == 1

    patched = await admin_client.patch(f"{PRODUCTS}/{pid}", json={"name": "Renamed"})
    assert patched.status_code == 200 and patched.json()["name"] == "Renamed"

    assert (await admin_client.delete(f"{PRODUCTS}/{pid}")).status_code == 204
    assert (await admin_client.get(PRODUCTS)).json() == []


async def test_admin_list_includes_inactive(admin_client):
    await admin_client.post(
        PRODUCTS, json={"name": "Hidden", "sku": _sku(), "is_active": False}
    )
    # admin sees inactive (unlike the public list)
    assert len((await admin_client.get(PRODUCTS)).json()) == 1


async def test_product_404s(admin_client):
    missing = f"{PRODUCTS}/{uuid.uuid4()}"
    assert (await admin_client.patch(missing, json={"name": "x"})).status_code == 404
    assert (await admin_client.delete(missing)).status_code == 404


async def test_product_validation(admin_client):
    # sku is required
    r = await admin_client.post(PRODUCTS, json={"name": "NoSku"})
    assert r.status_code == 422


async def test_upload_product_image(admin_client):
    created = await admin_client.post(PRODUCTS, json={"name": "P", "sku": _sku()})
    pid = created.json()["id"]
    r = await admin_client.post(
        f"{PRODUCTS}/{pid}/image",
        files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
    )
    assert r.status_code == 200
    assert r.json()["image_url"].startswith("/media/")


async def test_upload_image_404(admin_client):
    r = await admin_client.post(
        f"{PRODUCTS}/{uuid.uuid4()}/image",
        files={"file": ("photo.png", b"x", "image/png")},
    )
    assert r.status_code == 404


# ---- FAQs ----
async def test_faq_crud(admin_client):
    created = await admin_client.post(FAQS, json={"question": "Q", "answer": "A"})
    assert created.status_code == 201
    fid = created.json()["id"]

    assert len((await admin_client.get(FAQS)).json()) == 1

    patched = await admin_client.patch(f"{FAQS}/{fid}", json={"answer": "Better"})
    assert patched.status_code == 200 and patched.json()["answer"] == "Better"

    assert (await admin_client.delete(f"{FAQS}/{fid}")).status_code == 204
    assert (await admin_client.get(FAQS)).json() == []


async def test_faq_404s(admin_client):
    missing = f"{FAQS}/{uuid.uuid4()}"
    assert (await admin_client.patch(missing, json={"answer": "x"})).status_code == 404
    assert (await admin_client.delete(missing)).status_code == 404
