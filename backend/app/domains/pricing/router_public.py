"""Public /prices route. Moved verbatim from app/api/v1/public.py during the
domain migration; registered with tags=["public"] so OpenAPI is unchanged."""

from fastapi import APIRouter, Response

from app.domains.pricing.service import get_gold_prices

router = APIRouter()


@router.get("/prices")
async def public_prices(response: Response) -> dict:
    """Live market rates (TGJU) for the storefront نرخ روز strip. Same payload as
    the admin board — it's public market data; the service's in-process cache +
    background refresh_loop do the throttling, so this adds no TGJU load."""
    response.headers["Cache-Control"] = "public, max-age=120"
    return await get_gold_prices()
