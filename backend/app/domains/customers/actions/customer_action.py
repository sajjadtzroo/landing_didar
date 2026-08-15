from datetime import UTC, datetime

from fastapi import HTTPException

from app.core.storage import get_storage, sniff_ok
from app.domains.customers.models import Customer, CustomerVerificationStatus
from app.domains.customers.schemas import CustomerUpdate
from app.shared.cqrs import BaseAction

_ALLOWED_DOC = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_DOCS = 5


class CustomerAction(BaseAction[Customer]):
    """Customer self-service writes: profile + verification documents."""

    model = Customer

    async def update_profile(
        self, customer: Customer, payload: CustomerUpdate
    ) -> Customer:
        customer.full_name = payload.full_name
        customer.store_name = payload.store_name
        return await self.commit_and_refresh(customer)

    async def add_document(
        self,
        customer: Customer,
        *,
        content_type: str | None,
        filename: str | None,
        data: bytes,
    ) -> Customer:
        """Attach an uploaded verification document; a fresh upload moves an
        unverified/rejected customer back to pending review."""
        if content_type not in _ALLOWED_DOC:
            raise HTTPException(415, detail="فرمت فایل پشتیبانی نمی‌شود")
        if len(customer.verification_documents) >= _MAX_DOCS:
            raise HTTPException(400, detail="حداکثر تعداد مدارک بارگذاری شده است")
        if not sniff_ok(content_type, data):
            raise HTTPException(415, detail="محتوای فایل با نوع آن هم‌خوانی ندارد")
        if len(data) > _MAX_DOC_BYTES:
            raise HTTPException(413, detail="حجم فایل زیاد است (حداکثر ۱۰ مگابایت)")
        url = await get_storage().save(filename or "document", data)
        # reassign (not append) so SQLAlchemy flags the JSONB change
        customer.verification_documents = [
            *customer.verification_documents,
            {
                "url": url,
                "filename": filename,
                "uploaded_at": datetime.now(UTC).isoformat(),
            },
        ]
        if customer.verification_status in (
            CustomerVerificationStatus.unverified,
            CustomerVerificationStatus.rejected,
        ):
            customer.verification_status = CustomerVerificationStatus.pending
            customer.rejection_reason = None
        return await self.commit_and_refresh(customer)

    async def remove_document(self, customer: Customer, idx: int) -> Customer:
        if customer.verification_status != CustomerVerificationStatus.pending:
            raise HTTPException(400, detail="فقط در وضعیت در انتظار بررسی قابل حذف است")
        if idx < 0 or idx >= len(customer.verification_documents):
            raise HTTPException(404, detail="مدرک یافت نشد")
        docs = list(customer.verification_documents)
        docs.pop(idx)
        customer.verification_documents = docs
        return await self.commit_and_refresh(customer)
