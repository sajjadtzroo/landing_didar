from fastapi import APIRouter, Depends, Query

from app.domains.users.dependencies import require_superadmin
from app.domains.users.queries import AuditLogQuery
from app.domains.users.schemas import AuditListOut, AuditOut

router = APIRouter(dependencies=[Depends(require_superadmin)])


@router.get("/audit", response_model=AuditListOut)
async def list_audit(
    audit: AuditLogQuery = Depends(),
    actor: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    items, total = await audit.admin_page(actor=actor, page=page, page_size=page_size)
    return AuditListOut(
        items=[AuditOut.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )
