"""Admin notification on new orders. SMS is the only channel; when no creds are
set it falls back to logging so dev/tests work out of the box. Add another
channel by writing a new adapter and branching in `get_adapter()`.
"""

from app.core.config import settings
from app.domains.orders.services.notifications.base import NotificationAdapter
from app.domains.orders.services.notifications.sms import LogSmsAdapter, SmsAdapter


def get_adapter() -> NotificationAdapter:
    if settings.sms_provider.lower() != "payamsms" or not settings.payamsms_username:
        # No creds configured => log to stdout so dev/tests never fail on a real send.
        return LogSmsAdapter()
    return SmsAdapter()


__all__ = [
    "NotificationAdapter",
    "SmsAdapter",
    "LogSmsAdapter",
    "get_adapter",
]
