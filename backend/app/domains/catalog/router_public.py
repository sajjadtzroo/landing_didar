"""Public catalog routes. Moved verbatim from app/api/v1/public.py during the
domain migration; registered with tags=["public"] so OpenAPI is unchanged."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.db import get_db
from app.domains.catalog.models import Product
from app.domains.catalog.schemas import ProductOut

router = APIRouter()

_CACHE_TTL = 60.0
_CACHE_CONTROL = "public, max-age=60"


@router.get("/products", response_model=list[ProductOut])
async def list_products(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get("cache:products")
    if cached is not None:
        return cached
    res = await db.execute(
        select(Product)
        .where(Product.is_active, Product.product_status != "not_for_sale")
        .order_by(Product.sort_order)
    )
    items = [ProductOut.model_validate(p) for p in res.scalars().all()]
    await cache_set("cache:products", items, _CACHE_TTL)
    return items


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Product).where(
            Product.slug == slug,
            Product.is_active,
            Product.product_status != "not_for_sale",
        )
    )
    product = res.scalar_one_or_none()
    if product is None:
        raise HTTPException(404, detail="Product not found")
    return product
