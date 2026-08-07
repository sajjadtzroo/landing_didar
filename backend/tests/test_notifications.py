"""Notification path: adapter selection + message formatting. No DB — the
background dispatch itself is a docker/e2e concern (and stubbed in conftest)."""

from types import SimpleNamespace

import pytest

from app.services.notifications import LogSmsAdapter, SmsAdapter, get_adapter
from app.services.notifications.base import format_order_message


def _fake_order():
    return SimpleNamespace(
        id="abc-123",
        reference="DG-ABC123",
        full_name="Ali Rezaei",
        phone="09121234567",
        store_name="Rezaei Jewelry",
        province="Tehran",
        total=300,
        items=[
            SimpleNamespace(product_name="Ring", unit_price=100, quantity=3),
            SimpleNamespace(product_name="Custom item", unit_price=None, quantity=1),
        ],
    )


def test_get_adapter_falls_back_to_log_without_creds():
    # Default config has no SMS_API_KEY, so the log adapter is used.
    assert isinstance(get_adapter(), LogSmsAdapter)


def test_get_adapter_uses_sms_when_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "sms_provider", "kavenegar")
    monkeypatch.setattr(settings, "sms_api_key", "test-key")
    assert isinstance(get_adapter(), SmsAdapter)


def test_format_order_message_lists_items_and_link():
    msg = format_order_message(_fake_order(), "http://x/admin/orders")
    assert "DG-ABC123" in msg
    assert "Ring ×3 @ 100" in msg
    assert "Custom item ×1 @ —" in msg  # None price renders as em dash
    assert msg.endswith("http://x/admin/orders/abc-123")


@pytest.mark.asyncio(loop_scope="session")
async def test_log_adapter_send_does_not_raise():
    await LogSmsAdapter().send_new_order(_fake_order(), "http://x/admin/orders")


# ---- SmsAdapter real HTTP path (mocked httpx, no network) ----
from app.services.notifications import sms as notif_sms  # noqa: E402


class _FakeResp:
    def __init__(self, raise_exc=None):
        self._raise = raise_exc
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if self._raise:
            raise self._raise


class _FakeClient:
    last = None

    def __init__(self, resp, *a, **k):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        _FakeClient.last = {"url": url, "params": params}
        return self._resp


@pytest.mark.asyncio(loop_scope="session")
async def test_sms_adapter_sends_formatted_order(monkeypatch):
    from app.core.config import settings

    resp = _FakeResp()
    _FakeClient.last = None
    monkeypatch.setattr(settings, "sms_api_key", "KEY123")
    monkeypatch.setattr(settings, "sms_sender", "10004321")
    monkeypatch.setattr(settings, "sms_admin_phone", "09120000000")
    monkeypatch.setattr(notif_sms.httpx, "AsyncClient", lambda *a, **k: _FakeClient(resp))

    order = _fake_order()
    await SmsAdapter().send_new_order(order, "http://x/admin/orders")

    assert "KEY123/sms/send.json" in _FakeClient.last["url"]
    p = _FakeClient.last["params"]
    assert p["receptor"] == "09120000000" and p["sender"] == "10004321"
    assert order.reference in p["message"]  # the formatted message is sent
    assert resp.raise_called is True


@pytest.mark.asyncio(loop_scope="session")
async def test_sms_adapter_propagates_http_error(monkeypatch):
    monkeypatch.setattr(
        notif_sms.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeClient(_FakeResp(raise_exc=RuntimeError("boom"))),
    )
    with pytest.raises(RuntimeError, match="boom"):
        await SmsAdapter().send_new_order(_fake_order(), "http://x/admin/orders")
