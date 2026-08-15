import secrets
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domains.catalog import Product
from app.domains.customers import Customer
from app.domains.orders.models import Order, OrderItem, OrderStatus, OrderStatusLog
from app.domains.orders.queries import OrderQuery
from app.domains.orders.schemas import OrderCreate
from app.shared.cqrs import BaseAction
from app.shared.validation import hash_ip

_REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars


def _reference() -> str:
    return "DG-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))


class CreateOrderAction(BaseAction[Order]):
    model = Order

    async def execute(
        self,
        payload: OrderCreate,
        *,
        idempotency_key: str | None,
        ip: str | None,
    ) -> Order:
        """Create an order, copying product name + price at order time.
        Line-item data comes from the live product (server-trusted), not the
        client."""
        # Load referenced products in one query; snapshot their name/weight.
        product_ids = [it.product_id for it in payload.items if it.product_id]
        products: dict = {}
        if product_ids:
            res = await self.db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
            products = {p.id: p for p in res.scalars()}

        # Order size is total GRAMS (wholesale gold — quantified by weight).
        total = Decimal(0)
        items: list[OrderItem] = []
        for it in payload.items:
            p = products.get(it.product_id) if it.product_id else None
            name = p.name if p else "Custom item"
            unit_weight = p.weight_grams if p else None
            if unit_weight is not None:
                total += Decimal(unit_weight) * it.quantity
            items.append(
                OrderItem(
                    product_id=p.id if p else None,
                    product_name=name,
                    unit_weight_grams=unit_weight,
                    quantity=it.quantity,
                )
            )

        order = Order(
            reference=_reference(),
            full_name=payload.full_name,
            phone=payload.phone,
            store_name=payload.store_name,
            province=payload.province,
            city=payload.city,
            contact_method=payload.contact_method,
            note=payload.note,
            status=OrderStatus.new,
            total=total,
            idempotency_key=idempotency_key or None,
            utm_source=payload.utm_source,
            utm_medium=payload.utm_medium,
            utm_campaign=payload.utm_campaign,
            referrer=payload.referrer,
            ip_hash=hash_ip(ip),
            items=items,
            status_log=[OrderStatusLog(from_status=None, to_status=OrderStatus.new)],
        )
        self.db.add(order)
        try:
            await self.db.commit()
        except IntegrityError:
            # Concurrent submit with the same Idempotency-Key won the race — the
            # row exists; return the winner instead of 500-ing on the unique
            # violation.
            await self.db.rollback()
            if idempotency_key:
                existing = await OrderQuery(self.db).by_idempotency_key(
                    idempotency_key
                )
                if existing:
                    return existing
            raise
        await self.db.refresh(order)
        return order

    async def checkout(
        self,
        payload: OrderCreate,
        *,
        idempotency_key: str | None,
        ip: str | None,
        customer_id: uuid.UUID | None,
    ) -> Order:
        """Guest checkout flow: no login required. A logged-in session still
        binds the phone from the verified customer (client value can't override
        it); guests supply their own phone, and a later OTP login with that
        phone claims the order — /me/orders links orders to customers by phone.
        """
        if customer_id is not None:
            customer = await self.db.get(Customer, customer_id)
            if customer is not None:
                payload.phone = customer.phone

        order = await self.execute(payload, idempotency_key=idempotency_key, ip=ip)

        # Auto-register the guest as a customer (identity = phone) so they show
        # up in the admin customers panel immediately; a later OTP login with
        # the same phone lands on this account. Separate commit — never rolls
        # back the order.
        if customer_id is None:
            exists = (
                await self.db.execute(
                    select(Customer).where(Customer.phone == payload.phone)
                )
            ).scalar_one_or_none()
            if exists is None:
                self.db.add(
                    Customer(
                        phone=payload.phone,
                        full_name=payload.full_name,
                        store_name=payload.store_name,
                    )
                )
                try:
                    await self.db.commit()
                except IntegrityError:
                    # concurrent order with same phone won the race
                    await self.db.rollback()
        return order
