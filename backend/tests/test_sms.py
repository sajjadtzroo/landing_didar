"""Unit tests for the one-off SMS sender (OTP codes). The Kavenegar HTTP call is
mocked — no real network — and the log fallback is asserted to skip HTTP entirely.
"""

import pytest

from app.core.config import settings
from app.services import sms as sms_mod

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeResp:
    def __init__(self, raise_exc=None):
        self._raise = raise_exc
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if self._raise:
            raise self._raise


class _FakeClient:
    """Stands in for httpx.AsyncClient as an async context manager."""

    last = None  # captures the outgoing request for assertions

    def __init__(self, resp, *a, **k):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        _FakeClient.last = {"url": url, "params": params}
        return self._resp


def _install(monkeypatch, resp):
    _FakeClient.last = None
    monkeypatch.setattr(settings, "sms_provider", "kavenegar")
    monkeypatch.setattr(settings, "sms_api_key", "KEY123")
    monkeypatch.setattr(settings, "sms_sender", "10004321")
    monkeypatch.setattr(sms_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(resp))


async def test_send_sms_calls_kavenegar_with_expected_request(monkeypatch):
    resp = _FakeResp()
    _install(monkeypatch, resp)

    await sms_mod.send_sms("09121234567", "کد ورود دیدار: 424242")

    assert _FakeClient.last is not None
    assert "KEY123/sms/send.json" in _FakeClient.last["url"]
    assert _FakeClient.last["params"] == {
        "receptor": "09121234567",
        "sender": "10004321",
        "message": "کد ورود دیدار: 424242",
    }
    assert resp.raise_called is True  # HTTP errors are surfaced


async def test_send_sms_propagates_http_error(monkeypatch):
    _install(monkeypatch, _FakeResp(raise_exc=RuntimeError("502")))
    with pytest.raises(RuntimeError, match="502"):
        await sms_mod.send_sms("09121234567", "hi")


async def test_send_sms_logs_instead_of_calling_when_no_key(monkeypatch):
    # No API key => log fallback; httpx must NOT be constructed at all.
    monkeypatch.setattr(settings, "sms_provider", "kavenegar")
    monkeypatch.setattr(settings, "sms_api_key", "")

    def _boom(*a, **k):  # fail loudly if the HTTP path is taken
        raise AssertionError("httpx should not be used in the log fallback")

    monkeypatch.setattr(sms_mod.httpx, "AsyncClient", _boom)
    assert await sms_mod.send_sms("09121234567", "hi") is None
