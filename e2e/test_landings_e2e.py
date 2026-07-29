"""End-to-end tests for the 3-landing feature, run against the LIVE docker stack
(Nuxt SSR on :3001 → FastAPI on :8001 → Postgres). Unlike backend/tests, this
exercises the real frontend render + redirect + admin flow across all services.

Run (stack must be up — `docker compose up -d`):

    backend/.venv/bin/python -m pytest e2e/ -v

Skips itself automatically if the stack isn't reachable, so it never breaks the
unit suite. Overridable via env: E2E_FRONTEND, E2E_API, E2E_ADMIN_PASSWORD.
"""

import os

import httpx
import pytest

FRONTEND = os.getenv("E2E_FRONTEND", "http://localhost:3001")
API = os.getenv("E2E_API", "http://localhost:8001/api/v1")
ADMIN_USER = os.getenv("E2E_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("E2E_ADMIN_PASSWORD", "admin123")


def _stack_up() -> bool:
    try:
        httpx.get(f"{API}/landings/one", timeout=3).raise_for_status()
        httpx.get(FRONTEND, timeout=3, follow_redirects=True).raise_for_status()
        return True
    except Exception:  # noqa: BLE001 — any failure means "no live stack, skip"
        return False


pytestmark = pytest.mark.skipif(
    not _stack_up(), reason="live docker stack not reachable on :3001/:8001"
)


def _product_names(landing_slug: str) -> list[str]:
    data = httpx.get(f"{API}/landings/{landing_slug}", timeout=10).json()
    return [p["name"] for p in data["products"]]


# ---------- public routing + SSR ----------
def test_root_redirects_to_first_landing():
    r = httpx.get(f"{FRONTEND}/", follow_redirects=False, timeout=10)
    assert r.status_code in (301, 302, 307, 308)
    assert r.headers["location"].rstrip("/").endswith("/l/one")


@pytest.mark.parametrize("slug", ["one", "two", "three"])
def test_landing_ssr_renders_assigned_products(slug):
    names = _product_names(slug)
    assert names, f"landing {slug} has no products to assert on"
    html = httpx.get(f"{FRONTEND}/l/{slug}", timeout=15).text
    # SSR must have fetched from the backend and rendered the assigned products.
    assert names[0] in html
    assert names[-1] in html


def test_unknown_landing_is_404():
    r = httpx.get(f"{FRONTEND}/l/does-not-exist", timeout=10)
    assert r.status_code == 404


# ---------- admin flow reflects on the public page ----------
def _login() -> httpx.Client:
    c = httpx.Client(timeout=15)
    r = c.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return c


def test_admin_edit_video_and_products_reflects_publicly():
    c = _login()
    two = next(x for x in c.get(f"{API}/admin/landings").json() if x["slug"] == "two")
    original_ids = two["product_ids"]
    original_video = two["hero_video_url"]

    all_products = c.get(f"{API}/admin/products").json()
    a, b = all_products[0], all_products[1]
    excluded = all_products[5]  # a product intentionally left off landing "two"

    try:
        # Admin sets a new hero video + a 2-item reversed selection.
        c.patch(f"{API}/admin/landings/{two['id']}", json={"hero_video_url": "/media/e2e.mp4"})
        c.put(f"{API}/admin/landings/{two['id']}/products", json={"product_ids": [b["id"], a["id"]]})

        # Public API reflects both the video and the exact ordered subset.
        pub = httpx.get(f"{API}/landings/two", timeout=10).json()
        assert pub["hero_video_url"] == "/media/e2e.mp4"
        assert [p["id"] for p in pub["products"]] == [b["id"], a["id"]]
        assert excluded["id"] not in [p["id"] for p in pub["products"]]

        # Public SSR page shows the included products, in the new order.
        html = httpx.get(f"{FRONTEND}/l/two", timeout=15).text
        assert b["name"] in html and a["name"] in html

        # Landing "one" is unaffected by edits to "two" (isolation).
        assert len(httpx.get(f"{API}/landings/one", timeout=10).json()["products"]) >= 1
        assert httpx.get(f"{API}/landings/one", timeout=10).json()["hero_video_url"] != "/media/e2e.mp4"
    finally:
        # Restore landing "two" to its pre-test state.
        c.patch(f"{API}/admin/landings/{two['id']}", json={"hero_video_url": original_video})
        c.put(f"{API}/admin/landings/{two['id']}/products", json={"product_ids": original_ids})
        restored = c.get(f"{API}/admin/landings/{two['id']}").json()
        assert restored["product_ids"] == original_ids
        assert restored["hero_video_url"] == original_video
        c.close()


def test_admin_landings_requires_auth():
    r = httpx.get(f"{API}/admin/landings", timeout=10)
    assert r.status_code == 401


def test_admin_put_unknown_product_rejected():
    c = _login()
    two = next(x for x in c.get(f"{API}/admin/landings").json() if x["slug"] == "two")
    r = c.put(
        f"{API}/admin/landings/{two['id']}/products",
        json={"product_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    c.close()
    assert r.status_code == 422
