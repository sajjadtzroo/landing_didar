from app.domains.users.models import AuditLog
from app.shared.cqrs import BaseQuery


class AuditLogQuery(BaseQuery[AuditLog]):
    model = AuditLog

    async def admin_page(
        self, *, actor: str | None, page: int, page_size: int
    ) -> tuple[list[AuditLog], int]:
        """(items, total), newest first. The audit endpoint's documented
        page_size limit is 200 (> the shared MAX_PAGE_SIZE cap of 100), so the
        offset/limit lives here instead of going through BaseQuery.page()."""
        stmt = self.stmt()
        if actor:
            stmt = stmt.where(AuditLog.actor == actor)
        total = await self.count(stmt)
        rows = await self.db.execute(
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.scalars().all()), total
