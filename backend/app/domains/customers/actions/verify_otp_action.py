from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import verify_otp_async
from app.domains.customers.models import Customer, OtpCode
from app.shared.cqrs import BaseAction

OTP_MAX_ATTEMPTS = 5  # wrong tries before a code is dead


class VerifyOtpAction(BaseAction[Customer]):
    model = Customer

    async def execute(self, phone: str, code: str) -> Customer:
        """Check ``code`` against the newest unconsumed row for the phone.
        A wrong guess burns an attempt (committed so it survives the 400);
        success consumes the code and gets-or-creates the customer
        (identity = phone) in the same commit."""
        otp = (
            (
                await self.db.execute(
                    select(OtpCode)
                    .where(OtpCode.phone == phone, OtpCode.consumed.is_(False))
                    .order_by(OtpCode.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        now = datetime.now(UTC)
        invalid = HTTPException(400, detail="کد نامعتبر یا منقضی شده است")
        if otp is None or otp.expires_at < now or otp.attempts >= OTP_MAX_ATTEMPTS:
            raise invalid
        if not await verify_otp_async(code, otp.code_hash):
            otp.attempts += 1
            await self.db.commit()
            raise invalid
        otp.consumed = True
        customer = (
            await self.db.execute(select(Customer).where(Customer.phone == phone))
        ).scalar_one_or_none()
        if customer is None:
            customer = Customer(phone=phone)
            self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
