import time
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
)
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip
from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.core.content_defaults import default_content
from app.models.faq import FAQ
from app.models.landing import Landing
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.product import Product
from app.schemas.faq import FAQOut
from app.schemas.landing import LandingDetailOut, LandingGroupOut
from app.schemas.order import OrderCreate, OrderCreatedOut, OrderTrackOut
from app.schemas.portfolio import PortfolioPublicOut
from app.schemas.product import ProductOut
from app.services import orders as order_service
from app.services.notifications import get_adapter

router = APIRouter()

# Public catalog data changes rarely (admin edits) and is identical per visitor,
# so a short in-process TTL cache removes the DB round-trip on the hot read paths
# and collapses tail latency. Staleness ceiling = TTL; per-worker (no shared store
# needed at this scale). ponytail: dict cache, swap for Redis if we go multi-node.
_CACHE_TTL = 60.0
_cache: dict[str, tuple[float, object]] = {}
_CACHE_CONTROL = "public, max-age=60"


def _cache_get(key: str):
    hit = _cache.get(key)
    return hit[1] if hit and hit[0] > time.monotonic() else None


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.monotonic() + _CACHE_TTL, value)


def bust_landing_cache(slug: str) -> None:
    """Drop a landing's cached payload so an admin edit shows immediately instead
    of after the TTL. Called by admin_landings on mutate."""
    _cache.pop(f"landing:{slug}", None)


def bust_portfolios_cache() -> None:
    """Drop the cached /portfolios payload so an admin edit shows immediately.
    Called by admin_portfolios on mutate."""
    _cache.pop("portfolios", None)


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def _resolve_groups(
    db: AsyncSession, raw_groups: list[dict]
) -> list[LandingGroupOut]:
    """Resolve each group's `product_ids` against the live catalog in one query.
    A product is dropped if it's missing or inactive (ids live in JSON, so there's
    no FK/CASCADE — we filter here). Shared by landings and portfolios."""
    wanted = {
        u
        for g in raw_groups
        for pid in (g.get("product_ids") or [])
        if (u := _as_uuid(pid)) is not None
    }
    by_id: dict[uuid.UUID, Product] = {}
    if wanted:
        rows = (
            await db.execute(
                select(Product).where(Product.id.in_(wanted), Product.is_active)
            )
        ).scalars().all()
        by_id = {p.id: p for p in rows}

    groups: list[LandingGroupOut] = []
    for g in raw_groups:
        items = [
            by_id[_as_uuid(pid)]
            for pid in (g.get("product_ids") or [])
            if _as_uuid(pid) in by_id
        ]
        groups.append(
            LandingGroupOut(
                title=g.get("title") or "",
                eyebrow=g.get("eyebrow"),
                description=g.get("description"),
                products=list(items),
            )
        )
    return groups


@router.get("/products", response_model=list[ProductOut])
async def list_products(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = _cache_get("products")
    if cached is not None:
        return cached
    res = await db.execute(
        select(Product).where(Product.is_active).order_by(Product.sort_order)
    )
    items = [ProductOut.model_validate(p) for p in res.scalars().all()]
    _cache_set("products", items)
    return items


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Product).where(Product.slug == slug, Product.is_active)
    )
    product = res.scalar_one_or_none()
    if product is None:
        raise HTTPException(404, detail="Product not found")
    return product


@router.get("/landings/{slug}", response_model=LandingDetailOut)
async def get_landing(
    slug: str, response: Response, db: AsyncSession = Depends(get_db)
):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = _cache_get(f"landing:{slug}")
    if cached is not None:
        return cached
    landing = (
        await db.execute(select(Landing).where(Landing.slug == slug))
    ).scalar_one_or_none()
    if landing is None:
        raise HTTPException(404, detail="Landing not found")
    content = landing.content or default_content()
    groups = await _resolve_groups(db, content.get("groups") or [])

    out = LandingDetailOut(
        slug=landing.slug,
        title=landing.title,
        hero_video_url=landing.hero_video_url,
        hero_poster_url=landing.hero_poster_url,
        content=content,
        groups=groups,
    )
    _cache_set(f"landing:{slug}", out)
    return out


@router.get("/portfolios", response_model=list[PortfolioPublicOut])
async def list_portfolios(response: Response, db: AsyncSession = Depends(get_db)):
    """Active portfolios (curated /shop sections), ordered, with each group's
    products resolved from the live catalog. Cached like the other public reads."""
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = _cache_get("portfolios")
    if cached is not None:
        return cached
    portfolios = (
        await db.execute(
            select(Portfolio)
            .where(Portfolio.is_active)
            .order_by(Portfolio.sort_order)
        )
    ).scalars().all()
    out = [
        PortfolioPublicOut(
            id=p.id,
            name=p.name,
            slug=p.slug,
            cover_image_url=p.cover_image_url,
            groups=await _resolve_groups(db, (p.content or {}).get("groups") or []),
        )
        for p in portfolios
    ]
    _cache_set("portfolios", out)
    return out


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = _cache_get("faqs")
    if cached is not None:
        return cached
    res = await db.execute(
        select(FAQ).where(FAQ.is_active).order_by(FAQ.sort_order)
    )
    items = [FAQOut.model_validate(f) for f in res.scalars().all()]
    _cache_set("faqs", items)
    return items


@router.get("/orders/track", response_model=OrderTrackOut)
async def track_order(
    reference: str,
    phone: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Account-less order tracking. Both reference AND the ordering phone must
    match — an unknown reference and a wrong phone return the SAME 404 so a
    reference can't be enumerated without the phone. Never cached (status changes).
    """
    response.headers["Cache-Control"] = "no-store"
    order = (
        await db.execute(select(Order).where(Order.reference == reference.strip()))
    ).scalar_one_or_none()
    if order is None or order.phone != phone.strip():
        raise HTTPException(404, detail="Order not found")
    return order


async def _notify(order_id, admin_url: str) -> None:
    """Background task: re-loads the order in a fresh session (the request session
    is closed by now) and notifies. Failure logs + retries once, never blocks."""
    from app.core.db import SessionLocal
    from app.models.order import Order

    adapter = get_adapter()
    async with SessionLocal() as db:
        order = await db.get(Order, order_id)
        if order is None:
            return
        for attempt in (1, 2):
            try:
                await adapter.send_new_order(order, admin_url)
                return
            except Exception:  # noqa: BLE001
                logger.exception("order notification failed (attempt {})", attempt)


@router.post("/orders", response_model=OrderCreatedOut, status_code=201)
@limiter.limit("5/hour")
async def create_order(
    request: Request,
    payload: OrderCreate,
    background: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    # Honeypot: bots fill hidden fields; pretend success without persisting.
    if payload.website:
        return OrderCreatedOut(reference="DG-000000", total=0)

    # Idempotency: a repeated key returns the original order (double-tap safe).
    if idempotency_key:
        existing = await order_service.get_order_by_key(db, idempotency_key)
        if existing:
            return OrderCreatedOut(reference=existing.reference, total=existing.total)

    order = await order_service.create_order(
        db, payload, idempotency_key, get_client_ip(request)
    )
    # Notify AFTER commit, in the background — never rolls back the order.
    background.add_task(_notify, order.id, settings.admin_order_base_url)
    return OrderCreatedOut(reference=order.reference, total=order.total)
