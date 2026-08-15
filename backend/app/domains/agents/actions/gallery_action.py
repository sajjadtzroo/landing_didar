from fastapi import HTTPException
from sqlalchemy import select

from app.domains.agents.models import MobileGalleryItem
from app.domains.agents.schemas import GalleryAssignIn, GallerySellIn
from app.domains.catalog import Product
from app.domains.serials import ProductSerial, ProductSerialStatus
from app.domains.serials import service as serial_service
from app.domains.users import AdminRole, User
from app.shared.cqrs import BaseAction


class GalleryAction(BaseAction[MobileGalleryItem]):
    model = MobileGalleryItem

    async def assign(self, payload: GalleryAssignIn) -> MobileGalleryItem:
        """تحویل اولیه کالا به ایجنت: an in-stock serial goes into the agent's
        bag. Guards: real agent account, known in-stock serial, and the piece
        must not already be in another bag (partial unique index backs the
        check). kind defaults from the product (sample vs sellable)."""
        agent = await self.db.get(User, payload.agent_id)
        if agent is None or agent.role != AdminRole.agent:
            raise HTTPException(404, detail="Agent not found")

        normalized = serial_service.normalize(payload.code)
        serial = (
            await self.db.execute(
                select(ProductSerial).where(ProductSerial.code == normalized)
            )
        ).scalar_one_or_none()
        if serial is None:
            raise HTTPException(404, detail="سریال یافت نشد")
        if serial.status != ProductSerialStatus.in_stock:
            raise HTTPException(
                409, detail="فقط سریال‌های موجود (فروخته‌نشده) قابل تحویل‌اند"
            )
        active = (
            await self.db.execute(
                select(MobileGalleryItem.id).where(
                    MobileGalleryItem.serial_id == serial.id,
                    MobileGalleryItem.status == "with_agent",
                )
            )
        ).scalar_one_or_none()
        if active:
            raise HTTPException(409, detail="این قطعه هم‌اکنون همراه یک ایجنت است")

        kind = payload.kind
        if kind is None:
            product = await self.db.get(Product, serial.product_id)
            kind = (
                "sample"
                if (product and product.product_status == "sample")
                else "sellable"
            )

        return await self.save(
            MobileGalleryItem(
                agent_id=payload.agent_id,
                serial_id=serial.id,
                kind=kind,
                note=payload.note,
            )
        )

    async def return_item(self, item: MobileGalleryItem) -> MobileGalleryItem:
        """ثبت برگشت ساده: the piece is physically back at the office."""
        if item.status != "with_agent":
            raise HTTPException(409, detail="این قطعه همراه ایجنت نیست")
        item.status = "returned"
        return await self.commit_and_refresh(item)

    async def quick_sell(
        self, item: MobileGalleryItem, agent: User, payload: GallerySellIn
    ) -> MobileGalleryItem:
        """فروش فوری در حالت محدود (WO 7.6): sell a carried sellable piece on
        the spot — the serial flips to sold with a passport event; no order
        row."""
        if item.status != "with_agent":
            raise HTTPException(409, detail="این قطعه همراه شما نیست")
        if item.kind != "sellable":
            raise HTTPException(409, detail="کالای نمونه قابل فروش نیست")
        # Row-lock the serial so two concurrent sells can't both pass the check.
        serial = (
            await self.db.execute(
                select(ProductSerial)
                .where(ProductSerial.id == item.serial_id)
                .with_for_update()
            )
        ).scalar_one()
        if serial.status != ProductSerialStatus.in_stock:
            raise HTTPException(409, detail="وضعیت سریال اجازه فروش نمی‌دهد")

        serial.status = ProductSerialStatus.sold
        serial_service.record_event(
            self.db,
            item.serial_id,
            "sold",
            {"quick_sale": True, "agent": agent.username},
        )
        item.status = "sold"
        if payload.note:
            item.note = payload.note
        return await self.commit_and_refresh(item)
