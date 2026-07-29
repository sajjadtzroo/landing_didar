"""Admin notification on new orders. SMS is the primary adapter; Telegram/Email
are stubs behind the same protocol. Swap by changing `settings.sms_provider` or
the `get_adapter()` factory below.
"""

from app.core.config import settings
from app.services.notifications.base import NotificationAdapter
from app.services.notifications.email import EmailAdapter
from app.services.notifications.sms import LogSmsAdapter, SmsAdapter
from app.services.notifications.telegram import TelegramAdapter


def get_adapter() -> NotificationAdapter:
    provider = settings.sms_provider.lower()
    if provider == "log" or not settings.sms_api_key:
        # No creds configured => log to stdout so dev/tests never fail on a real send.
        return LogSmsAdapter()
    return SmsAdapter()


__all__ = [
    "NotificationAdapter",
    "SmsAdapter",
    "LogSmsAdapter",
    "TelegramAdapter",
    "EmailAdapter",
    "get_adapter",
]
