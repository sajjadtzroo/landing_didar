import httpx
from loguru import logger

from app.core.config import settings
from app.models.order import Order
from app.services.notifications.base import format_order_message


class SmsAdapter:
    """Kavenegar-style HTTP SMS. Swap the provider by changing the URL/params here
    (or add another branch keyed on settings.sms_provider) — the protocol stays put.
    """

    async def send_new_order(self, order: Order, admin_url: str) -> None:
        message = format_order_message(order, admin_url)
        url = (
            f"https://api.kavenegar.com/v1/{settings.sms_api_key}/sms/send.json"
        )
        params = {
            "receptor": settings.sms_admin_phone,
            "sender": settings.sms_sender,
            "message": message,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()


class LogSmsAdapter:
    """Fallback used when no SMS creds are set — logs instead of sending so dev
    and tests work out of the box. Also the SMS/Email/Telegram 'stub' behavior."""

    async def send_new_order(self, order: Order, admin_url: str) -> None:
        logger.info(
            "[SMS stub] to {}:\n{}",
            settings.sms_admin_phone or "<unset>",
            format_order_message(order, admin_url),
        )
