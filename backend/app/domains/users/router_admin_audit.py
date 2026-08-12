from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.domains.users.dependencies import require_superadmin
from app.domains.users.models import AuditLog
from app.domains.users.schemas import AuditListOut, AuditOut

router = APIRouter(dependencies=[Depends(require_superadmin)])


@router.get("/audit", response_model=AuditListOut)
async def list_audit(
    db: AsyncSession = Depends(get_db),
    actor: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(AuditLog)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await db.execute(
        stmt.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [AuditOut.model_validate(a) for a in rows.scalars().all()]
    return AuditListOut(items=items, total=total or 0, page=page, page_size=page_size)
