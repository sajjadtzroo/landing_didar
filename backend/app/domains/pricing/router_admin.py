"""Admin gold-price board — live TGJU rates for pricing reference."""

from fastapi import APIRouter, Depends

from app.domains.pricing.service import get_gold_prices
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/prices")
async def prices() -> dict:
    return await get_gold_prices()
