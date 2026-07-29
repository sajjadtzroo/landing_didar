import uuid

import pytest
import pytest_asyncio

from app.models.landing import Landing

pytestmark = pytest.mark.asyncio(loop_scope="session")

PUB = "/api/v1/landings"
ADMIN = "/api/v1/admin/landings"


@pytest_asyncio.fixture
def make_landing(_sessionmaker):
    # Landings are seeded in prod (no create endpoint); tests insert directly.
    async def make(slug="one", title="L1"):
        async with _sessionmaker() as s:
            ln = Landing(
                slug=slug, title=title,
                hero_video_url="/media/hero.mp4",
                hero_poster_url="/media/hero-poster.jpg",
            )
            s.add(ln)
            await s.commit()
            await s.refresh(ln)
            return {"id": str(ln.id), "slug": ln.slug}
    return make


async def _make_product(admin_client, **over):
    body = {"name": "Ring", "sku": f"R-{uuid.uuid4().hex[:8]}", **over}
    r = await admin_client.post("/api/v1/admin/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _assign(admin_client, landing_id, ids):
    return await admin_client.put(
        f"{ADMIN}/{landing_id}/products", json={"product_ids": ids}
    )


# ---- Public GET /landings/{slug} ----
async def test_get_landing_404(client):
    assert (await client.get(f"{PUB}/nope")).status_code == 404


async def test_get_landing_returns_active_products_in_order(
    client, admin_client, make_landing
):
    ln = await make_landing()
    p1 = await _make_product(admin_client, name="First")
    p2 = await _make_product(admin_client, name="Second")
    hidden = await _make_product(admin_client, name="Hidden", is_active=False)

    # assign in the order p2, p1, hidden
    await _assign(admin_client, ln["id"], [p2, p1, hidden])

    body = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert body["slug"] == "one"
    assert body["hero_video_url"] == "/media/hero.mp4"
    # inactive excluded; active kept in assignment order
    assert [p["name"] for p in body["products"]] == ["Second", "First"]


# ---- Admin ----
async def test_admin_requires_auth(client):
    assert (await client.get(ADMIN)).status_code == 401


async def test_admin_list_and_get(admin_client, make_landing):
    ln = await make_landing()
    listed = (await admin_client.get(ADMIN)).json()
    assert [x["slug"] for x in listed] == ["one"]
    one = (await admin_client.get(f"{ADMIN}/{ln['id']}")).json()
    assert one["title"] == "L1" and one["product_ids"] == []


async def test_admin_patch_updates_meta_not_slug(admin_client, make_landing):
    ln = await make_landing()
    r = await admin_client.patch(
        f"{ADMIN}/{ln['id']}",
        json={"title": "New", "hero_video_url": "/media/hero2.mp4", "slug": "hacked"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "New"
    assert body["hero_video_url"] == "/media/hero2.mp4"
    assert body["slug"] == "one"  # slug immutable — extra field ignored


async def test_admin_put_products_replaces_and_reorders(
    admin_client, make_landing
):
    ln = await make_landing()
    a = await _make_product(admin_client)
    b = await _make_product(admin_client)
    c = await _make_product(admin_client)

    first = await _assign(admin_client, ln["id"], [a, b, c])
    assert first.json()["product_ids"] == [a, b, c]

    # replace with a reordered subset
    second = await _assign(admin_client, ln["id"], [c, a])
    assert second.json()["product_ids"] == [c, a]


async def test_admin_put_unknown_product_422(admin_client, make_landing):
    ln = await make_landing()
    r = await _assign(admin_client, ln["id"], [str(uuid.uuid4())])
    assert r.status_code == 422


async def test_admin_put_dedupes(admin_client, make_landing):
    ln = await make_landing()
    a = await _make_product(admin_client)
    r = await _assign(admin_client, ln["id"], [a, a])
    assert r.json()["product_ids"] == [a]


async def test_deleting_product_cascades_assignment(admin_client, make_landing):
    ln = await make_landing()
    a = await _make_product(admin_client)
    b = await _make_product(admin_client)
    await _assign(admin_client, ln["id"], [a, b])

    await admin_client.delete(f"/api/v1/admin/products/{a}")

    body = (await admin_client.get(f"{ADMIN}/{ln['id']}")).json()
    assert body["product_ids"] == [b]  # deleted product's assignment gone
