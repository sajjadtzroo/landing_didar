"""Admin portfolio CRUD — thin HTTP layer over PortfolioQuery / PortfolioAction."""

from fastapi import APIRouter, Depends

from app.domains.content.actions import PortfolioAction
from app.domains.content.queries import PortfolioQuery
from app.domains.content.schemas import (
    PortfolioAdminOut,
    PortfolioCreate,
    PortfolioUpdate,
)
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/portfolios", response_model=list[PortfolioAdminOut])
async def list_portfolios(portfolios: PortfolioQuery = Depends()):
    return [
        PortfolioAdminOut.model_validate(p) for p in await portfolios.list_admin()
    ]


@router.post("/portfolios", response_model=PortfolioAdminOut, status_code=201)
async def create_portfolio(
    payload: PortfolioCreate, action: PortfolioAction = Depends()
):
    return PortfolioAdminOut.model_validate(await action.create(payload))


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioAdminOut)
async def get_portfolio(portfolio_id: str, portfolios: PortfolioQuery = Depends()):
    return PortfolioAdminOut.model_validate(
        await portfolios.by_id_or_404(portfolio_id, detail="Portfolio not found")
    )


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioAdminOut)
async def update_portfolio(
    portfolio_id: str,
    payload: PortfolioUpdate,
    portfolios: PortfolioQuery = Depends(),
    action: PortfolioAction = Depends(),
):
    portfolio = await portfolios.by_id_or_404(
        portfolio_id, detail="Portfolio not found"
    )
    return PortfolioAdminOut.model_validate(await action.update(portfolio, payload))


@router.delete("/portfolios/{portfolio_id}", status_code=204)
async def delete_portfolio(
    portfolio_id: str,
    portfolios: PortfolioQuery = Depends(),
    action: PortfolioAction = Depends(),
):
    portfolio = await portfolios.by_id_or_404(
        portfolio_id, detail="Portfolio not found"
    )
    await action.delete(portfolio)
