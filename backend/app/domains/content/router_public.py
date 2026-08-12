"""Public content routes (landings, portfolios, FAQs).

Moved verbatim from app/api/v1/public.py during the domain migration; paths,
tags and response models are unchanged (registered with tags=["public"])."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.content_defaults import default_content
from app.core.db import get_db
from app.domains.content.models import FAQ, Landing, Portfolio
from app.domains.content.schemas import FAQOut, LandingDetailOut, PortfolioPublicOut
from app.domains.content.service import resolve_groups

router = APIRouter()

# Public catalog data changes rarely (admin edits) and is identical per visitor,
# so a short TTL cache removes the DB round-trip on the hot read paths and
# collapses tail latency. Backed by app.core.cache: in-process dict by default,
# shared Redis when REDIS_URL is set (multi-worker/multi-node coherent busts).
_CACHE_TTL = 60.0
_CACHE_CONTROL = "public, max-age=60"


@router.get("/landings/{slug}", response_model=LandingDetailOut)
async def get_landing(
    slug: str, response: Response, db: AsyncSession = Depends(get_db)
):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get(f"cache:landing:{slug}")
    if cached is not None:
        return cached
    landing = (
        await db.execute(select(Landing).where(Landing.slug == slug))
    ).scalar_one_or_none()
    if landing is None:
        raise HTTPException(404, detail="Landing not found")
    content = landing.content or default_content()
    groups = await resolve_groups(db, content.get("groups") or [])

    out = LandingDetailOut(
        slug=landing.slug,
        title=landing.title,
        hero_video_url=landing.hero_video_url,
        hero_poster_url=landing.hero_poster_url,
        content=content,
        groups=groups,
    )
    await cache_set(f"cache:landing:{slug}", out, _CACHE_TTL)
    return out


@router.get("/portfolios", response_model=list[PortfolioPublicOut])
async def list_portfolios(response: Response, db: AsyncSession = Depends(get_db)):
    """Active portfolios (curated /shop sections), ordered, with each group's
    products resolved from the live catalog. Cached like the other public reads."""
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get("cache:portfolios")
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
            groups=await resolve_groups(db, (p.content or {}).get("groups") or []),
        )
        for p in portfolios
    ]
    await cache_set("cache:portfolios", out, _CACHE_TTL)
    return out


@router.get("/portfolios/{slug}", response_model=PortfolioPublicOut)
async def get_portfolio(
    slug: str, response: Response, db: AsyncSession = Depends(get_db)
):
    """A single curated collection by slug, for its /shop/<slug> page. Inactive
    portfolios 404 (matching the list). Cached per slug like get_landing."""
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get(f"cache:portfolio:{slug}")
    if cached is not None:
        return cached
    portfolio = (
        await db.execute(
            select(Portfolio).where(Portfolio.slug == slug, Portfolio.is_active)
        )
    ).scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(404, detail="Portfolio not found")
    out = PortfolioPublicOut(
        id=portfolio.id,
        name=portfolio.name,
        slug=portfolio.slug,
        cover_image_url=portfolio.cover_image_url,
        groups=await resolve_groups(db, (portfolio.content or {}).get("groups") or []),
    )
    await cache_set(f"cache:portfolio:{slug}", out, _CACHE_TTL)
    return out


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get("cache:faqs")
    if cached is not None:
        return cached
    res = await db.execute(select(FAQ).where(FAQ.is_active).order_by(FAQ.sort_order))
    items = [FAQOut.model_validate(f) for f in res.scalars().all()]
    await cache_set("cache:faqs", items, _CACHE_TTL)
    return items
