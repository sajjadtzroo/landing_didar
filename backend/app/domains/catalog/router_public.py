"""Public catalog routes. Moved from app/api/v1/public.py during the domain
migration; registered with tags=["public"]."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.db import get_db
from app.domains.catalog.models import Product
from app.domains.catalog.schemas import ProductOut

router = APIRouter()

_CACHE_TTL = 60.0
_CACHE_CONTROL = "public, max-age=60"

# Serialize once per cache window, not per request: validating 500+ ORM rows
# through Pydantic on every cache HIT was the measured hot-path ceiling
# (docs/perf/capacity-2026-08-12.md). The cache stores the finished JSON body;
# hits return it as-is.
_products_json = TypeAdapter(list[ProductOut])

_ACTIVE = (Product.is_active, Product.product_status != "not_for_sale")


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=60, ge=1, le=100),
):
    """Active catalog, ordered. Without `page` the full list is returned
    (existing storefront contract). With `page`, a slice of `page_size` plus an
    `X-Total-Count` header — the response stays a plain array either way."""
    key = f"cache:products:p{page}:s{page_size}" if page else "cache:products"
    cached = await cache_get(key)
    if cached is not None:
        total, body = cached
        return Response(
            content=body,
            media_type="application/json",
            headers={"Cache-Control": _CACHE_CONTROL, "X-Total-Count": str(total)},
        )

    q = (
        select(Product)
        .where(*_ACTIVE)
        # secondary key makes page boundaries deterministic on sort_order ties
        .order_by(Product.sort_order, Product.id)
    )
    if page:
        total = await db.scalar(
            select(func.count()).select_from(Product).where(*_ACTIVE)
        )
        q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    if not page:
        total = len(rows)

    body = _products_json.dump_json(
        [ProductOut.model_validate(p) for p in rows]
    ).decode()
    await cache_set(key, [total, body], _CACHE_TTL)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Cache-Control": _CACHE_CONTROL, "X-Total-Count": str(total)},
    )


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
