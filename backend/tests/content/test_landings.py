import uuid

import pytest
import pytest_asyncio

from app.domains.content import Landing

pytestmark = pytest.mark.asyncio(loop_scope="session")

PUB = "/api/v1/landings"
ADMIN = "/api/v1/admin/landings"


@pytest_asyncio.fixture
def make_landing(_sessionmaker):
    # Landings are seeded in prod (no create endpoint); tests insert directly.
    async def make(slug="one", title="L1"):
        async with _sessionmaker() as s:
            ln = Landing(
                slug=slug,
                title=title,
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


def _group(product_ids, title="G", eyebrow=None, description=None):
    return {
        "title": title,
        "eyebrow": eyebrow,
        "description": description,
        "product_ids": product_ids,
    }


async def _set_groups(admin_client, landing_id, groups):
    """Products are assigned by editing the landing's content JSON (groups hold
    the ordered product ids). PATCH replaces content and busts the read cache."""
    r = await admin_client.patch(
        f"{ADMIN}/{landing_id}", json={"content": {"groups": groups}}
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---- Public GET /landings/{slug} ----
async def test_get_landing_404(client):
    assert (await client.get(f"{PUB}/nope")).status_code == 404


async def test_group_products_resolved_active_and_in_order(
    client, admin_client, make_landing
):
    ln = await make_landing(slug="grp-order")
    p1 = await _make_product(admin_client, name="First")
    p2 = await _make_product(admin_client, name="Second")
    hidden = await _make_product(admin_client, name="Hidden", is_active=False)

    # assign in the order p2, p1, hidden
    await _set_groups(admin_client, ln["id"], [_group([p2, p1, hidden])])

    body = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert body["slug"] == "grp-order"
    assert body["hero_video_url"] == "/media/hero.mp4"
    # one group; inactive excluded; active kept in assignment order
    assert len(body["groups"]) == 1
    assert [p["name"] for p in body["groups"][0]["products"]] == ["Second", "First"]


async def test_unknown_product_ids_are_dropped_not_errored(
    client, admin_client, make_landing
):
    ln = await make_landing(slug="grp-unknown")
    a = await _make_product(admin_client, name="Real")
    ghost = str(uuid.uuid4())  # never created

    # unknown ids live only in JSON (no FK), so they're silently dropped on read
    await _set_groups(admin_client, ln["id"], [_group([a, ghost])])

    body = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert [p["name"] for p in body["groups"][0]["products"]] == ["Real"]


async def test_deleting_product_drops_it_from_public_output(
    client, admin_client, make_landing
):
    ln = await make_landing(slug="grp-del")
    a = await _make_product(admin_client, name="Gone")
    b = await _make_product(admin_client, name="Stays")
    await _set_groups(admin_client, ln["id"], [_group([a, b])])

    await admin_client.delete(f"/api/v1/admin/products/{a}")

    # GET once, after the delete — the deleted product resolves to nothing
    body = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert [p["name"] for p in body["groups"][0]["products"]] == ["Stays"]


# ---- Admin ----
async def test_admin_requires_auth(client):
    assert (await client.get(ADMIN)).status_code == 401


async def test_admin_list_and_get(admin_client, make_landing):
    ln = await make_landing()
    listed = (await admin_client.get(ADMIN)).json()
    assert [x["slug"] for x in listed] == ["one"]
    one = (await admin_client.get(f"{ADMIN}/{ln['id']}")).json()
    assert one["title"] == "L1"
    assert one["content"] is None  # freshly seeded, no content yet
    assert "product_ids" not in one  # flat assignment API is gone


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


async def test_admin_patch_groups_replaces_and_reorders(
    client, admin_client, make_landing
):
    ln = await make_landing(slug="grp-replace")
    a = await _make_product(admin_client)
    b = await _make_product(admin_client)
    c = await _make_product(admin_client)

    await _set_groups(admin_client, ln["id"], [_group([a, b, c])])
    first = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert [p["id"] for p in first["groups"][0]["products"]] == [a, b, c]

    # replace with a reordered subset (PATCH busts the cache)
    await _set_groups(admin_client, ln["id"], [_group([c, a])])
    second = (await client.get(f"{PUB}/{ln['slug']}")).json()
    assert [p["id"] for p in second["groups"][0]["products"]] == [c, a]
