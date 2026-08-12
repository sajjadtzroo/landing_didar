"""One-off SMS sends (OTP codes, admin order alerts) via PayamSMS.

PayamSMS REST v2.1 (آتیه داده پرداز): OAuth2 password-grant login at
/auth/oauth/token (Basic client header), then Bearer-token sends at
/panel/webservice/send with a JSON array of messages. Re-login before expiry
returns the same token, so the cache below just re-logs-in when stale.

Falls back to logging when provider is "log" or creds are missing, so dev and
tests work out of the box.
"""

import asyncio
import base64
import time

import httpx
from loguru import logger

from app.core.config import settings

BASE_URL = "https://www.payamsms.com"

# Token cache: re-login when missing or within the safety margin of expiry.
# The doc warns expires_in may change server-side — always trust the response.
_token: str | None = None
_token_expires_at: float = 0.0
_token_lock = asyncio.Lock()
_TOKEN_SAFETY_S = 60

_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=10)
    return _client


def _to98(phone: str) -> str:
    """Normalize to the 98-prefixed form PayamSMS requires (09… → 989…)."""
    p = phone.strip().lstrip("+")
    if p.startswith("0"):
        p = "98" + p[1:]
    return p


async def _login() -> str:
    basic = base64.b64encode(
        f"{settings.payamsms_client_id}:{settings.payamsms_client_secret}".encode()
    ).decode()
    resp = await _http().post(
        "/auth/oauth/token",
        headers={"Authorization": f"Basic {basic}"},
        json={
            "systemName": settings.payamsms_system_name,
            "username": settings.payamsms_username,
            "password": settings.payamsms_password,
            "scope": "webservice",
            "grant_type": "password",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    global _token, _token_expires_at
    _token = data["access_token"]
    _token_expires_at = time.monotonic() + float(data["expires_in"]) - _TOKEN_SAFETY_S
    return _token


async def _get_token() -> str:
    async with _token_lock:
        if _token and time.monotonic() < _token_expires_at:
            return _token
        return await _login()


def _drop_token() -> None:
    global _token
    _token = None


class SmsSendError(RuntimeError):
    """Raised when PayamSMS rejects a message (errorCode in the response item)."""

    def __init__(self, error_code: str, description: str | None = None):
        self.error_code = error_code
        super().__init__(f"payamsms send failed: {error_code} ({description})")


async def send_sms(to: str, message: str) -> None:
    if settings.sms_provider.lower() != "payamsms" or not settings.payamsms_username:
        logger.info("[SMS stub] to {}: {}", to, message)
        return

    payload = [
        {"sender": settings.sms_sender, "recipient": _to98(to), "body": message}
    ]
    token = await _get_token()
    resp = await _http().post(
        "/panel/webservice/send",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if resp.status_code == 401:
        # Token invalidated server-side before our expiry margin — one retry.
        _drop_token()
        token = await _get_token()
        resp = await _http().post(
            "/panel/webservice/send",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    resp.raise_for_status()

    item = resp.json()[0]
    if "errorCode" in item and item["errorCode"]:
        # Per the doc: build logic on errorCode; description may change.
        logger.error(
            "payamsms rejected sms to {}: {} {}",
            to,
            item["errorCode"],
            item.get("description"),
        )
        raise SmsSendError(item["errorCode"], item.get("description"))
