"""Stub: Telegram adapter behind the same protocol. Wire it up and return it from
get_adapter() to switch the primary channel to Telegram."""

import httpx

from app.core.config import settings
from app.models.order import Order
from app.services.notifications.base import format_order_message


class TelegramAdapter:
    async def send_new_order(self, order: Order, admin_url: str) -> None:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": format_order_message(order, admin_url),
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
