from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.domains.serials.actions.serial_action import SerialAction
from app.domains.serials.models import BuybackRequest, ProductSerial
from app.domains.serials.queries import BuybackQuery
from app.domains.serials.schemas import BuybackCreate, BuybackUpdate
from app.shared.cqrs import BaseAction


class BuybackAction(BaseAction[BuybackRequest]):
    model = BuybackRequest

    async def request(
        self, serial: ProductSerial, payload: BuybackCreate
    ) -> BuybackRequest:
        """ثبت درخواست بازخرید (WO 7.9). One open request per piece at a time —
        the partial unique index is the DB backstop for this check-then-insert."""
        if await BuybackQuery(self.db).has_open(serial.id):
            raise HTTPException(
                409, detail="برای این قطعه یک درخواست در حال بررسی وجود دارد"
            )
        req = BuybackRequest(
            serial_id=serial.id,
            requester_name=payload.full_name,
            requester_phone=payload.phone,
            note=payload.note,
        )
        self.db.add(req)
        SerialAction(self.db).record_event(serial.id, "buyback_requested")
        try:
            await self.db.commit()
        except IntegrityError:
            # Concurrent request won the race on the partial-unique open-request index.
            await self.db.rollback()
            raise HTTPException(
                409, detail="برای این قطعه یک درخواست در حال بررسی وجود دارد"
            ) from None
        return req

    async def update_admin(
        self, buyback: BuybackRequest, payload: BuybackUpdate
    ) -> BuybackRequest:
        """Admin review: status / offered_price / admin_note — one commit."""
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(buyback, k, v)
        return await self.commit_and_refresh(buyback)
