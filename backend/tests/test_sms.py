"""Unit tests for the PayamSMS client (OTP codes + order alerts share it).
All HTTP is faked at the module's client — no real network."""

import pytest

from app.core.config import settings
from app.shared import sms as sms_mod
from app.shared.sms import SmsSendError, _to98

pytestmark = pytest.mark.asyncio(loop_scope="session")

TOKEN_RESP = {"access_token": "TOK1", "expires_in": 3600, "scope": "webservice"}
SEND_OK = [{"customerId": None, "mobile": 989121234567, "serverId": "SRV1"}]


class _FakeResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeHttp:
    """Stands in for the module-level httpx.AsyncClient."""

    def __init__(self, responses):
        # responses: list of (path-substring, _FakeResp) consumed in order for /send;
        # /token always answered from token_resp (counted).
        self.calls = []
        self.send_responses = list(responses)
        self.login_count = 0

    async def post(self, path, headers=None, json=None):
        self.calls.append({"path": path, "headers": headers, "json": json})
        if "oauth/token" in path:
            self.login_count += 1
            return _FakeResp(TOKEN_RESP)
        return self.send_responses.pop(0)


def _install(monkeypatch, send_responses):
    fake = _FakeHttp(send_responses)
    monkeypatch.setattr(settings, "sms_provider", "payamsms")
    monkeypatch.setattr(settings, "payamsms_username", "didar")
    monkeypatch.setattr(settings, "payamsms_password", "pw")
    monkeypatch.setattr(settings, "payamsms_system_name", "didargold")
    monkeypatch.setattr(settings, "payamsms_client_id", "cid")
    monkeypatch.setattr(settings, "payamsms_client_secret", "csecret")
    monkeypatch.setattr(settings, "sms_sender", "9820001234")
    monkeypatch.setattr(sms_mod, "_client", fake)
    # reset token cache between tests
    monkeypatch.setattr(sms_mod, "_token", None)
    monkeypatch.setattr(sms_mod, "_token_expires_at", 0.0)
    return fake


def test_to98_normalizes_local_numbers():
    assert _to98("09121234567") == "989121234567"
    assert _to98("989121234567") == "989121234567"
    assert _to98("+989121234567") == "989121234567"


async def test_send_logs_in_then_sends_with_bearer_and_98_number(monkeypatch):
    fake = _install(monkeypatch, [_FakeResp(SEND_OK)])

    await sms_mod.send_sms("09121234567", "کد ورود دیدار: 424242")

    login, send = fake.calls
    assert "oauth/token" in login["path"]
    assert login["headers"]["Authorization"].startswith("Basic ")
    assert login["json"]["grant_type"] == "password"
    assert login["json"]["scope"] == "webservice"

    assert send["path"] == "/panel/webservice/send"
    assert send["headers"]["Authorization"] == "Bearer TOK1"
    assert send["json"] == [
        {
            "sender": "9820001234",
            "recipient": "989121234567",
            "body": "کد ورود دیدار: 424242",
        }
    ]


async def test_token_is_cached_across_sends(monkeypatch):
    fake = _install(monkeypatch, [_FakeResp(SEND_OK), _FakeResp(SEND_OK)])
    await sms_mod.send_sms("09121234567", "one")
    await sms_mod.send_sms("09121234567", "two")
    assert fake.login_count == 1  # second send reused the cached token


async def test_401_triggers_one_relogin_and_retry(monkeypatch):
    fake = _install(
        monkeypatch, [_FakeResp({}, status_code=401), _FakeResp(SEND_OK)]
    )
    await sms_mod.send_sms("09121234567", "hi")
    assert fake.login_count == 2  # initial login + re-login after 401
    assert len([c for c in fake.calls if c["path"].endswith("/send")]) == 2


async def test_error_code_in_response_raises(monkeypatch):
    _install(
        monkeypatch,
        [_FakeResp([{"mobile": 989121234567, "errorCode": "E6",
                     "description": "no credit"}])],
    )
    with pytest.raises(SmsSendError) as exc:
        await sms_mod.send_sms("09121234567", "hi")
    assert exc.value.error_code == "E6"


async def test_log_provider_skips_http_entirely(monkeypatch):
    monkeypatch.setattr(settings, "sms_provider", "log")

    def _boom():
        raise AssertionError("http client must not be touched in log mode")

    monkeypatch.setattr(sms_mod, "_http", _boom)
    assert await sms_mod.send_sms("09121234567", "hi") is None
