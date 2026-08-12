"""Public /prices endpoint (storefront نرخ روز strip). Service mocked — no TGJU."""

import pytest

import app.domains.pricing.router_public as public

pytestmark = pytest.mark.asyncio(loop_scope="session")

_CANNED = {
    "items": [
        {
            "symbol": "geram18",
            "label": "طلای ۱۸ عیار (هر گرم)",
            "unit": "toman",
            "price": 18_900_000,
            "change_pct": 1.2,
            "direction": "high",
            "updated_at": "۱۵:۰۰:۰۰",
        }
    ],
    "source": "tgju",
    "cached": True,
}


async def test_public_prices_returns_board_with_cache_header(client, monkeypatch):
    async def _fake():
        return _CANNED

    monkeypatch.setattr(public, "get_gold_prices", _fake)
    r = await client.get("/api/v1/prices")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=120"
    body = r.json()
    assert body["items"][0]["symbol"] == "geram18"
    assert body["items"][0]["price"] == 18_900_000


async def test_public_prices_requires_no_auth(client, monkeypatch):
    async def _fake():
        return {"items": [], "source": "tgju", "error": True}

    monkeypatch.setattr(public, "get_gold_prices", _fake)
    # No admin/customer cookie on `client` — must still be 200 (public market data).
    assert (await client.get("/api/v1/prices")).status_code == 200
