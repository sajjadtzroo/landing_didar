"""Generic one-off SMS send (OTP login codes). Order alerts use the richer
notification adapters; this is the minimal 'send a string to a phone' path.
Falls back to logging when no creds are configured so dev/tests work out of box.
"""

import httpx
from loguru import logger

from app.core.config import settings


async def send_sms(to: str, message: str) -> None:
    if settings.sms_provider.lower() == "log" or not settings.sms_api_key:
        logger.info("[SMS stub] to {}: {}", to, message)
        return
    url = f"https://api.kavenegar.com/v1/{settings.sms_api_key}/sms/send.json"
    params = {"receptor": to, "sender": settings.sms_sender, "message": message}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
