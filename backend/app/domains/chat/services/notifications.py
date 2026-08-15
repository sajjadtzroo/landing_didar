"""Staff alerting for new/reopened chat inquiries (fire-and-forget SMS)."""

import asyncio

from loguru import logger

from app.core.config import settings
from app.shared.sms import send_sms


async def notify_admin_new_conversation() -> None:
    """SMS the shop admin that a customer is waiting. Best-effort: chat keeps
    working when the gateway is down, staff just rely on the inbox badge."""
    if not settings.sms_admin_phone:
        return
    try:
        await send_sms(
            settings.sms_admin_phone,
            "دیدار: گفتگوی پشتیبانی جدید — مشتری منتظر پاسخ است.",
        )
    except Exception as e:  # noqa: BLE001 — alert failure must not break chat
        logger.warning("chat admin sms failed: {}", e)


def spawn_admin_alert() -> None:
    # Fire-and-forget so the customer's request doesn't wait on the SMS API.
    asyncio.get_running_loop().create_task(notify_admin_new_conversation())
