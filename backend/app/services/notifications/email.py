"""Stub: Email adapter (SMTP/Resend) behind the same protocol. Fill in and return
from get_adapter() to switch the primary channel to email."""

from app.models.order import Order
from app.services.notifications.base import format_order_message


class EmailAdapter:
    async def send_new_order(self, order: Order, admin_url: str) -> None:  # noqa: D401
        # ponytail: stub — wire SMTP or Resend here when email becomes the channel.
        _ = format_order_message(order, admin_url)
        raise NotImplementedError("EmailAdapter is a stub — configure SMTP/Resend")
