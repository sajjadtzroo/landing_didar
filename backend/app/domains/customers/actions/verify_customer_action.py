from datetime import UTC, datetime

from app.domains.customers.models import Customer, CustomerVerificationStatus
from app.domains.customers.schemas import VerificationUpdate
from app.shared.cqrs import BaseAction
from app.shared.sms import send_sms

APPROVED_SMS = "احراز هویت شما با موفقیت انجام شد."


class VerifyCustomerAction(BaseAction[Customer]):
    """Admin verification decision: approve/reject + notification SMS."""

    model = Customer

    async def execute(
        self, customer: Customer, payload: VerificationUpdate
    ) -> Customer:
        new = CustomerVerificationStatus(payload.status)
        if customer.verification_status == new:
            return customer  # same decision twice is a no-op — never re-SMS
        customer.verification_status = new
        if new == CustomerVerificationStatus.approved:
            customer.verified_at = datetime.now(UTC)
            customer.rejection_reason = None
            await send_sms(customer.phone, APPROVED_SMS)
        else:  # rejected
            customer.rejection_reason = payload.reason
            await send_sms(
                customer.phone, f"مدارک شما تایید نشد. {payload.reason or ''}".strip()
            )
        return await self.commit_and_refresh(customer)
