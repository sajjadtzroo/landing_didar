"""Admin gold-price board — live TGJU rates for pricing reference."""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.domains.pricing.service import get_gold_prices

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/prices")
async def prices() -> dict:
    return await get_gold_prices()
