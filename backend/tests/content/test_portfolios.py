import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

PUB = "/api/v1/portfolios"
ADMIN = "/api/v1/admin/portfolios"


async def _make_product(admin_client, **over):
    body = {"name": "Ring", "sku": f"R-{uuid.uuid4().hex[:8]}", **over}
    r = await admin_client.post("/api/v1/admin/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create(admin_client, name="Eid", slug="eid"):
    r = await admin_client.post(ADMIN, json={"name": name, "slug": slug})
    assert r.status_code == 201, r.text
    return r.json()


async def _set_groups(admin_client, pid, groups, **fields):
    r = await admin_client.patch(
        f"{ADMIN}/{pid}", json={"content": {"groups": groups}, **fields}
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---- Admin auth ----
async def test_admin_requires_auth(client):
    assert (await client.get(ADMIN)).status_code == 401


# ---- Admin CRUD ----
async def test_create_and_get(admin_client):
    pf = await _create(admin_client)
    assert pf["is_active"] is True and pf["content"] == {"groups": []}
    got = (await admin_client.get(f"{ADMIN}/{pf['id']}")).json()
    assert got["name"] == "Eid" and got["slug"] == "eid"


async def test_duplicate_slug_409(admin_client):
    await _create(admin_client, slug="dup")
    r = await admin_client.post(ADMIN, json={"name": "Other", "slug": "dup"})
    assert r.status_code == 409


async def test_bad_slug_422(admin_client):
    r = await admin_client.post(ADMIN, json={"name": "X", "slug": "Bad Slug!"})
    assert r.status_code == 422


async def test_patch_meta_and_delete(admin_client):
    pf = await _create(admin_client)
    r = await admin_client.patch(
        f"{ADMIN}/{pf['id']}",
        json={"name": "Renamed", "is_active": False, "sort_order": 5,
              "cover_image_url": "/media/c.jpg"},
    )
    assert r.status_code == 200
    b = r.json()
    assert b["name"] == "Renamed" and b["is_active"] is False
    assert b["sort_order"] == 5 and b["cover_image_url"] == "/media/c.jpg"
    assert (await admin_client.delete(f"{ADMIN}/{pf['id']}")).status_code == 204
    assert (await admin_client.get(f"{ADMIN}/{pf['id']}")).status_code == 404


# ---- Public GET /portfolios ----
async def test_public_resolves_and_orders(client, admin_client):
    p1 = await _make_product(admin_client, name="First")
    p2 = await _make_product(admin_client, name="Second")
    hidden = await _make_product(admin_client, name="Hidden", is_active=False)

    pf = await _create(admin_client, name="Coll", slug="coll")
    # group products in order p2, p1, hidden — hidden must drop, order preserved
    await _set_groups(
        admin_client,
        pf["id"],
        [{"title": "G1", "eyebrow": "e", "description": "d",
          "product_ids": [p2, p1, hidden]}],
    )

    body = (await client.get(PUB)).json()
    assert len(body) == 1
    assert body[0]["name"] == "Coll"
    assert body[0]["groups"][0]["title"] == "G1"
    assert [p["name"] for p in body[0]["groups"][0]["products"]] == ["Second", "First"]


async def test_public_hides_inactive_and_sorts(client, admin_client):
    a = await _create(admin_client, name="A", slug="a")
    b = await _create(admin_client, name="B", slug="b")
    # B first (sort_order 0), A second (sort_order 1); one inactive portfolio hidden
    await _set_groups(admin_client, a["id"], [], sort_order=1)
    await _set_groups(admin_client, b["id"], [], sort_order=0)
    hidden = await _create(admin_client, name="H", slug="h")
    await _set_groups(admin_client, hidden["id"], [], is_active=False)

    names = [p["name"] for p in (await client.get(PUB)).json()]
    assert names == ["B", "A"]  # inactive excluded, ordered by sort_order


# ---- Public GET /portfolios/{slug} (per-collection page) ----
async def test_public_by_slug_resolves_groups(client, admin_client):
    p1 = await _make_product(admin_client, name="First")
    p2 = await _make_product(admin_client, name="Second")
    hidden = await _make_product(admin_client, name="Hidden", is_active=False)

    pf = await _create(admin_client, name="Eid Collection", slug="eid-collection")
    await _set_groups(
        admin_client,
        pf["id"],
        [{"title": "G1", "eyebrow": "e", "description": "d",
          "product_ids": [p2, p1, hidden]}],
    )

    body = (await client.get(f"{PUB}/eid-collection")).json()
    assert body["name"] == "Eid Collection" and body["slug"] == "eid-collection"
    # inactive dropped, order preserved
    assert [p["name"] for p in body["groups"][0]["products"]] == ["Second", "First"]


async def test_public_by_slug_unknown_404(client):
    assert (await client.get(f"{PUB}/nope")).status_code == 404


async def test_public_by_slug_inactive_404(client, admin_client):
    pf = await _create(admin_client, name="Hidden", slug="hidden-coll")
    await _set_groups(admin_client, pf["id"], [], is_active=False)
    assert (await client.get(f"{PUB}/hidden-coll")).status_code == 404


async def test_by_slug_cache_busts_on_edit(client, admin_client):
    a = await _make_product(admin_client, name="A")
    b = await _make_product(admin_client, name="B")
    pf = await _create(admin_client, name="Spring", slug="spring")
    await _set_groups(
        admin_client, pf["id"], [{"title": "G", "product_ids": [a]}]
    )

    first = (await client.get(f"{PUB}/spring")).json()  # caches under portfolio:spring
    assert [p["name"] for p in first["groups"][0]["products"]] == ["A"]

    # editing busts the per-slug cache, so the next read reflects the change
    await _set_groups(
        admin_client, pf["id"], [{"title": "G", "product_ids": [a, b]}]
    )
    second = (await client.get(f"{PUB}/spring")).json()
    assert [p["name"] for p in second["groups"][0]["products"]] == ["A", "B"]
