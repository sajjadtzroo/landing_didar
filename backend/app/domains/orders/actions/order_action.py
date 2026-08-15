from datetime import UTC, datetime

from app.domains.orders.models import Order, OrderStatus, OrderStatusLog
from app.domains.orders.schemas import OrderUpdate
from app.shared.cqrs import BaseAction

# serials' public API itself imports orders (allowed by the DAG), so importing
# serials at module scope here would make orders.__init__ circular — the two
# serial calls below import lazily instead.


class OrderAction(BaseAction[Order]):
    model = Order

    async def change_status(self, order: Order, to_status: OrderStatus) -> None:
        """Append to the status log + stamp delivered_at on first delivery.
        Does NOT commit — the calling command's transaction owns it."""
        if order.status == to_status:
            return
        order.status_log.append(
            OrderStatusLog(from_status=order.status, to_status=to_status)
        )
        order.status = to_status
        # Proof of Delivery: stamp the first time the order becomes delivered.
        if to_status == OrderStatus.delivered and order.delivered_at is None:
            order.delivered_at = datetime.now(UTC)

    async def update_admin(self, order: Order, payload: OrderUpdate) -> Order:
        """Admin PATCH: status transition (+ serial minting on delivery),
        notes, read flag, proof of delivery — one commit."""
        if payload.status is not None:
            await self.change_status(order, payload.status)
            # Delivered => mint one authenticity serial per piece (idempotent).
            if order.status == OrderStatus.delivered:
                from app.domains.serials import SerialAction

                await SerialAction(self.db).generate_for_order(order)
        if payload.internal_note is not None:
            order.internal_note = payload.internal_note
        if payload.is_read is not None:
            order.is_read = payload.is_read
        if payload.delivery_assignee is not None:
            order.delivery_assignee = payload.delivery_assignee
        if payload.delivery_proof is not None:
            order.delivery_proof = payload.delivery_proof.model_dump(
                exclude_none=True
            )
        return await self.commit_and_refresh(order)

    async def mint_serials(self, order: Order) -> list[str]:
        """Manual fallback: mint serials for an order (e.g. delivered before
        this feature existed). Idempotent — returns the order's codes whether
        it minted now or already had them."""
        from app.domains.serials import SerialAction

        await SerialAction(self.db).generate_for_order(order)
        await self.commit_and_refresh(order)
        return order.serial_codes
