import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_otp_async
from app.domains.customers.models import OtpCode
from app.shared.cqrs import BaseAction
from app.shared.sms import send_sms

OTP_TTL = 300  # seconds a code stays valid
# Per-PHONE cap, DB-backed: the route's slowapi limit is per-IP, so an attacker
# rotating IPs could SMS-bomb one victim's phone. Counting rows makes the cap
# exact across workers and immune to cache eviction.
OTP_PER_PHONE_PER_HOUR = 5


class RequestOtpAction(BaseAction[OtpCode]):
    model = OtpCode

    async def execute(self, phone: str) -> str | None:
        """Store a hashed one-time code (one row per request) and deliver it.
        Returns the code when it may be revealed to the client, else None."""
        recent = await self.db.scalar(
            select(func.count())
            .select_from(OtpCode)
            .where(
                OtpCode.phone == phone,
                OtpCode.created_at > datetime.now(UTC) - timedelta(hours=1),
            )
        )
        if (recent or 0) >= OTP_PER_PHONE_PER_HOUR:
            raise HTTPException(
                429, detail="تعداد درخواست کد بیش از حد مجاز است؛ بعداً تلاش کنید"
            )
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.db.add(
            OtpCode(
                phone=phone,
                code_hash=await hash_otp_async(code),
                expires_at=datetime.now(UTC) + timedelta(seconds=OTP_TTL),
            )
        )
        await self.db.commit()
        # Allowlisted test phones skip the real gateway and get the code back
        # directly (QA / app-review logins in prod). Everyone else gets a real SMS.
        is_test = phone in settings.otp_test_phone_set
        if not is_test:
            await send_sms(phone, f"کد ورود دیدار: {code}")
        # dev_code outside production, or for test phones even in production.
        reveal = is_test or not settings.cookie_secure
        return code if reveal else None
