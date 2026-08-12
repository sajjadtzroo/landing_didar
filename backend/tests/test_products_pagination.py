"""Public /products: serialized-JSON cache + optional pagination."""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_products(admin_client, n=5):
    for i in range(n):
        r = await admin_client.post(
            "/api/v1/admin/products",
            json={"name": f"p{i}", "slug": f"pg-{i}", "sku": f"PG-{i}",
                  "sort_order": i},
        )
        assert r.status_code == 201, r.text


async def test_unpaginated_returns_full_list_with_total(client, admin_client):
    await _make_products(admin_client, 5)
    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    assert len(r.json()) == 5
    assert r.headers["x-total-count"] == "5"


async def test_page_slices_and_total(client, admin_client):
    await _make_products(admin_client, 5)
    r1 = await client.get("/api/v1/products?page=1&page_size=2")
    r2 = await client.get("/api/v1/products?page=2&page_size=2")
    r3 = await client.get("/api/v1/products?page=3&page_size=2")
    assert [p["slug"] for p in r1.json()] == ["pg-0", "pg-1"]
    assert [p["slug"] for p in r2.json()] == ["pg-2", "pg-3"]
    assert [p["slug"] for p in r3.json()] == ["pg-4"]
    assert r1.headers["x-total-count"] == "5"


async def test_cache_hit_serves_identical_body(client, admin_client):
    await _make_products(admin_client, 3)
    first = await client.get("/api/v1/products")
    # second request is a cache hit (60s TTL) — same body, no re-serialization
    second = await client.get("/api/v1/products")
    assert first.content == second.content
    assert second.headers["x-total-count"] == "3"


async def test_page_beyond_end_is_empty_list(client, admin_client):
    await _make_products(admin_client, 2)
    r = await client.get("/api/v1/products?page=9&page_size=50")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["x-total-count"] == "2"
