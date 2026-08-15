from loguru import logger

from app.core.config import settings
from app.domains.orders.models import Order
from app.domains.orders.services.notifications.base import format_order_message
from app.shared.sms import send_sms


class SmsAdapter:
    """Order alerts ride the shared PayamSMS client — one provider integration
    (app/shared/sms.py) serves both OTP codes and these notifications."""

    async def send_new_order(self, order: Order, admin_url: str) -> None:
        await send_sms(
            settings.sms_admin_phone, format_order_message(order, admin_url)
        )


class LogSmsAdapter:
    """Fallback used when no SMS creds are set — logs instead of sending so dev
    and tests work out of the box. Also the SMS/Email/Telegram 'stub' behavior."""

    async def send_new_order(self, order: Order, admin_url: str) -> None:
        logger.info(
            "[SMS stub] to {}:\n{}",
            settings.sms_admin_phone or "<unset>",
            format_order_message(order, admin_url),
        )
