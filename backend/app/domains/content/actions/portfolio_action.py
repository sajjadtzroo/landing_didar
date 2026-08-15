from fastapi import HTTPException

from app.domains.content.models import Portfolio
from app.domains.content.queries import PortfolioQuery
from app.domains.content.schemas import PortfolioCreate, PortfolioUpdate
from app.domains.content.services import bust_portfolio_cache, bust_portfolios_cache
from app.shared.cqrs import BaseAction

_SLUG_CLASH = "A portfolio with this slug already exists"


class PortfolioAction(BaseAction[Portfolio]):
    model = Portfolio

    async def create(self, payload: PortfolioCreate) -> Portfolio:
        if await PortfolioQuery(self.db).slug_taken(payload.slug):
            raise HTTPException(409, detail=_SLUG_CLASH)
        portfolio = await self.save(
            Portfolio(name=payload.name, slug=payload.slug, content={"groups": []})
        )
        await bust_portfolios_cache()
        return portfolio

    async def update(self, portfolio: Portfolio, payload: PortfolioUpdate) -> Portfolio:
        old_slug = portfolio.slug
        data = payload.model_dump(exclude_unset=True)
        # A slug edit must stay unique.
        if "slug" in data and data["slug"] != portfolio.slug:
            if await PortfolioQuery(self.db).slug_taken(data["slug"]):
                raise HTTPException(409, detail=_SLUG_CLASH)
        for k, v in data.items():
            setattr(portfolio, k, v)
        portfolio = await self.commit_and_refresh(portfolio)
        await bust_portfolios_cache()
        # Bust the old slug; the new slug (if changed) was never cached.
        await bust_portfolio_cache(old_slug)
        if portfolio.slug != old_slug:
            await bust_portfolio_cache(portfolio.slug)
        return portfolio

    async def delete(self, portfolio: Portfolio) -> None:
        slug = portfolio.slug
        await super().delete(portfolio)
        await bust_portfolios_cache()
        await bust_portfolio_cache(slug)
