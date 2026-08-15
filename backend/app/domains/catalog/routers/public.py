"""Public catalog routes. Moved from app/api/v1/public.py during the domain
migration; registered with tags=["public"]."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import TypeAdapter

from app.core.cache import cache_get, cache_set
from app.domains.catalog.queries import ProductQuery
from app.domains.catalog.schemas import ProductOut
from app.domains.catalog.services.cache import products_cache_key

router = APIRouter()

_CACHE_TTL = 60.0
_CACHE_CONTROL = "public, max-age=60"

# Serialize once per cache window, not per request: validating 500+ ORM rows
# through Pydantic on every cache HIT was the measured hot-path ceiling
# (docs/perf/capacity-2026-08-12.md). The cache stores the finished JSON body;
# hits return it as-is.
_products_json = TypeAdapter(list[ProductOut])


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    products: ProductQuery = Depends(),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=60, ge=1, le=100),
):
    """Active catalog, ordered. Without `page` the full list is returned
    (existing storefront contract). With `page`, a slice of `page_size` plus an
    `X-Total-Count` header — the response stays a plain array either way."""
    key = await products_cache_key(page, page_size)
    cached = await cache_get(key)
    if cached is not None:
        total, body = cached
        return Response(
            content=body,
            media_type="application/json",
            headers={"Cache-Control": _CACHE_CONTROL, "X-Total-Count": str(total)},
        )

    rows, total = await products.active_page(page=page, page_size=page_size)

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
async def get_product(
    slug: str, response: Response, products: ProductQuery = Depends()
):
    product = await products.active_by_slug(slug)
    if product is None:
        raise HTTPException(404, detail="Product not found")
    # Same 60s window as the list — lets the browser/proxy absorb repeat hits.
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return product
