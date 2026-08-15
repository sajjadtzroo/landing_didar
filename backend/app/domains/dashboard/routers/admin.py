"""Admin dashboard stats — thin HTTP layer over DashboardQuery."""

from fastapi import APIRouter, Depends

from app.domains.dashboard.queries import DashboardQuery
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/stats")
async def stats(dashboard: DashboardQuery = Depends()):
    return await dashboard.stats()
