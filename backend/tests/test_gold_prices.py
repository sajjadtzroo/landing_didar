"""Unit tests for the TGJU gold-price scraper. httpx is mocked — no network."""

import pytest

import app.services.gold_prices as mod

pytestmark = pytest.mark.asyncio(loop_scope="session")

_SAMPLE = {
    "current": {
        "geram18": {"p": "189,048,000", "dp": 1.76, "dt": "high", "t": "۱۵:۲۷:۲۹"},
        "price_dollar_rl": {"p": "1,862,850", "dp": 0.92, "dt": "low", "t": "۱۵:۲۷:۲۹"},
        "ons": {"p": "4,343.43", "dp": 0.14, "dt": "high", "t": "۱۵:۲۷:۲۹"},
        "unknown_symbol": {"p": "1", "dp": 0},  # ignored (not in SYMBOLS)
    }
}


class _Resp:
    def __init__(self, payload, exc=None):
        self._p = payload
        self._exc = exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._p


class _Client:
    def __init__(self, payload=None, exc=None):
        self._resp = _Resp(payload, exc)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        return self._resp


@pytest.fixture(autouse=True)
def _reset_cache():
    mod._cache.update({"at": 0.0, "items": None})
    yield
    mod._cache.update({"at": 0.0, "items": None})


async def test_parses_and_converts_rial_to_toman(monkeypatch):
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: _Client(_SAMPLE))
    out = await mod.get_gold_prices(force=True)
    assert out["source"] == "tgju" and out["cached"] is False
    by = {i["symbol"]: i for i in out["items"]}

    assert "unknown_symbol" not in by  # only curated symbols
    assert by["geram18"]["price"] == 18_904_800  # 189,048,000 rial / 10 = toman
    assert by["geram18"]["change_pct"] == 1.76
    assert by["geram18"]["direction"] == "high"
    assert by["price_dollar_rl"]["price"] == 186_285  # 1,862,850 / 10
    # ounce is USD — NOT divided by 10, kept as a float
    assert by["ons"]["unit"] == "usd" and by["ons"]["price"] == 4343.43


async def test_second_call_within_ttl_is_cached(monkeypatch):
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: _Client(_SAMPLE))
    first = await mod.get_gold_prices(force=True)

    # Any further HTTP must NOT happen; if it did, this client would blow up.
    def _boom(*a, **k):
        raise AssertionError("should have used the cache, not refetched")

    monkeypatch.setattr(mod.httpx, "AsyncClient", _boom)
    second = await mod.get_gold_prices()
    assert second["cached"] is True
    assert second["items"] == first["items"]


async def test_error_without_cache_returns_error_flag(monkeypatch):
    monkeypatch.setattr(
        mod.httpx, "AsyncClient", lambda *a, **k: _Client(exc=RuntimeError("502"))
    )
    out = await mod.get_gold_prices(force=True)
    assert out["error"] is True and out["items"] == []


async def test_error_with_cache_serves_stale(monkeypatch):
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: _Client(_SAMPLE))
    await mod.get_gold_prices(force=True)  # warm the cache
    monkeypatch.setattr(
        mod.httpx, "AsyncClient", lambda *a, **k: _Client(exc=RuntimeError("down"))
    )
    out = await mod.get_gold_prices(force=True)  # force a refetch that fails
    assert out.get("stale") is True and out["items"]  # last good snapshot
