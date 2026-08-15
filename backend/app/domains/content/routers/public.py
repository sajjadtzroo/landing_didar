"""Public content routes (landings, portfolios, FAQs).

Moved verbatim from app/api/v1/public.py during the domain migration; paths,
tags and response models are unchanged (registered with tags=["public"])."""

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.cache import cache_get, cache_set
from app.core.content_defaults import default_content
from app.domains.content.queries import FaqQuery, LandingQuery, PortfolioQuery
from app.domains.content.schemas import FAQOut, LandingDetailOut, PortfolioPublicOut

router = APIRouter()

# Public catalog data changes rarely (admin edits) and is identical per visitor,
# so a short TTL cache removes the DB round-trip on the hot read paths and
# collapses tail latency. Backed by app.core.cache: in-process dict by default,
# shared Redis when REDIS_URL is set (multi-worker/multi-node coherent busts).
_CACHE_TTL = 60.0
_CACHE_CONTROL = "public, max-age=60"


@router.get("/landings/{slug}", response_model=LandingDetailOut)
async def get_landing(
    slug: str, response: Response, landings: LandingQuery = Depends()
):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get(f"cache:landing:{slug}")
    if cached is not None:
        return cached
    landing = await landings.by_slug(slug)
    if landing is None:
        raise HTTPException(404, detail="Landing not found")
    content = landing.content or default_content()
    groups = await landings.resolve_groups(content.get("groups") or [])

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
async def list_portfolios(response: Response, portfolios: PortfolioQuery = Depends()):
    """Active portfolios (curated /shop sections), ordered, with each group's
    products resolved from the live catalog. Cached like the other public reads."""
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get("cache:portfolios")
    if cached is not None:
        return cached
    out = [
        PortfolioPublicOut(
            id=p.id,
            name=p.name,
            slug=p.slug,
            cover_image_url=p.cover_image_url,
            groups=await portfolios.resolve_groups(
                (p.content or {}).get("groups") or []
            ),
        )
        for p in await portfolios.list_public()
    ]
    await cache_set("cache:portfolios", out, _CACHE_TTL)
    return out


@router.get("/portfolios/{slug}", response_model=PortfolioPublicOut)
async def get_portfolio(
    slug: str, response: Response, portfolios: PortfolioQuery = Depends()
):
    """A single curated collection by slug, for its /shop/<slug> page. Inactive
    portfolios 404 (matching the list). Cached per slug like get_landing."""
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get(f"cache:portfolio:{slug}")
    if cached is not None:
        return cached
    portfolio = await portfolios.by_slug_public(slug)
    if portfolio is None:
        raise HTTPException(404, detail="Portfolio not found")
    out = PortfolioPublicOut(
        id=portfolio.id,
        name=portfolio.name,
        slug=portfolio.slug,
        cover_image_url=portfolio.cover_image_url,
        groups=await portfolios.resolve_groups(
            (portfolio.content or {}).get("groups") or []
        ),
    )
    await cache_set(f"cache:portfolio:{slug}", out, _CACHE_TTL)
    return out


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(response: Response, faqs: FaqQuery = Depends()):
    response.headers["Cache-Control"] = _CACHE_CONTROL
    cached = await cache_get("cache:faqs")
    if cached is not None:
        return cached
    items = [FAQOut.model_validate(f) for f in await faqs.list_public()]
    await cache_set("cache:faqs", items, _CACHE_TTL)
    return items
