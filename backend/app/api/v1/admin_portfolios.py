from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.v1.public import bust_portfolio_cache, bust_portfolios_cache
from app.core.db import get_db
from app.models.portfolio import Portfolio
from app.schemas.portfolio import (
    PortfolioAdminOut,
    PortfolioCreate,
    PortfolioUpdate,
)

router = APIRouter(dependencies=[Depends(require_admin)])


async def _get_or_404(db: AsyncSession, portfolio_id: str) -> Portfolio:
    portfolio = await db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(404, detail="Portfolio not found")
    return portfolio


@router.get("/portfolios", response_model=list[PortfolioAdminOut])
async def list_portfolios(db: AsyncSession = Depends(get_db)):
    portfolios = (
        await db.execute(select(Portfolio).order_by(Portfolio.sort_order))
    ).scalars().all()
    return [PortfolioAdminOut.model_validate(p) for p in portfolios]


@router.post("/portfolios", response_model=PortfolioAdminOut, status_code=201)
async def create_portfolio(
    payload: PortfolioCreate, db: AsyncSession = Depends(get_db)
):
    exists = await db.scalar(
        select(Portfolio.id).where(Portfolio.slug == payload.slug)
    )
    if exists:
        raise HTTPException(409, detail="A portfolio with this slug already exists")
    portfolio = Portfolio(
        name=payload.name, slug=payload.slug, content={"groups": []}
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    await bust_portfolios_cache()
    return PortfolioAdminOut.model_validate(portfolio)


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioAdminOut)
async def get_portfolio(portfolio_id: str, db: AsyncSession = Depends(get_db)):
    return PortfolioAdminOut.model_validate(await _get_or_404(db, portfolio_id))


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioAdminOut)
async def update_portfolio(
    portfolio_id: str, payload: PortfolioUpdate, db: AsyncSession = Depends(get_db)
):
    portfolio = await _get_or_404(db, portfolio_id)
    old_slug = portfolio.slug
    data = payload.model_dump(exclude_unset=True)
    # A slug edit must stay unique.
    if "slug" in data and data["slug"] != portfolio.slug:
        clash = await db.scalar(
            select(Portfolio.id).where(Portfolio.slug == data["slug"])
        )
        if clash:
            raise HTTPException(409, detail="A portfolio with this slug already exists")
    for k, v in data.items():
        setattr(portfolio, k, v)
    await db.commit()
    await db.refresh(portfolio)
    await bust_portfolios_cache()
    await bust_portfolio_cache(old_slug)  # bust old slug; new slug (if changed) was uncached
    if portfolio.slug != old_slug:
        await bust_portfolio_cache(portfolio.slug)
    return PortfolioAdminOut.model_validate(portfolio)


@router.delete("/portfolios/{portfolio_id}", status_code=204)
async def delete_portfolio(portfolio_id: str, db: AsyncSession = Depends(get_db)):
    portfolio = await _get_or_404(db, portfolio_id)
    slug = portfolio.slug
    await db.delete(portfolio)
    await db.commit()
    await bust_portfolios_cache()
    await bust_portfolio_cache(slug)
