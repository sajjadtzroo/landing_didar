"""CQRS-light base classes — the "Common" layer of the modular backend.

Layer contract (full rules + rationale: app/domains/CLAUDE.md):

    router  -> Query / Action / schemas   thin HTTP: no select(), no db.commit()
    Action  -> models, Query, services, other domains' PUBLIC API
               owns the write transaction (commit lives here, nowhere else)
    Query   -> models only — read side, never flushes or commits
    service -> stateless integration helpers (SMS, storage, realtime)

Both classes are cheap per-request objects wired by FastAPI DI — the session
arrives via Depends(get_db), so an endpoint declares collaborators instead of
touching the session:

    @router.get("/orders/{order_id}")
    async def get_order(order_id: str, orders: OrderQuery = Depends()):
        return await orders.by_id_or_404(order_id)

Outside a request (tests, background tasks, seeds) construct them directly
with any AsyncSession: ``OrderQuery(db)``.
"""

from collections.abc import Iterable
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

# Hard cap — no endpoint may page more than this, whatever the client asks for.
MAX_PAGE_SIZE = 100


class _SessionBound:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db


class BaseQuery[TModel](_SessionBound):
    """Read side of a domain. Subclasses set ``model`` and add named readers.

    Every reader builds on ``self.stmt()`` (a fresh Select) — never mutate or
    cache statements on the instance. A Query must not flush, commit, or hold
    state beyond the session.
    """

    model: type[TModel]

    def stmt(self) -> Select[tuple[TModel]]:
        return select(type(self).model)

    async def by_id(self, ident: Any) -> TModel | None:
        return await self.db.get(type(self).model, ident)

    async def by_id_or_404(self, ident: Any, detail: str = "Not found") -> TModel:
        obj = await self.by_id(ident)
        if obj is None:
            raise HTTPException(404, detail=detail)
        return obj

    async def one_or_none(self, stmt: Select[tuple[TModel]]) -> TModel | None:
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def all(self, stmt: Select[tuple[TModel]]) -> list[TModel]:
        return list((await self.db.execute(stmt)).scalars().all())

    async def count(self, stmt: Select) -> int:
        n = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        return n or 0

    async def page(
        self,
        stmt: Select[tuple[TModel]],
        *,
        page: int,
        page_size: int,
        order_by: Iterable[Any] = (),
    ) -> tuple[list[TModel], int]:
        """(items, total) with the MAX_PAGE_SIZE cap applied server-side."""
        page_size = min(page_size, MAX_PAGE_SIZE)
        total = await self.count(stmt)
        rows = await self.db.execute(
            stmt.order_by(*order_by).offset((page - 1) * page_size).limit(page_size)
        )
        return list(rows.scalars().all()), total


class BaseAction[TModel](_SessionBound):
    """Write side of a domain. Subclasses set ``model`` and add named commands.

    Actions own the transaction: a router never calls db.commit() — it calls a
    single Action method that validates, mutates, and commits. Multi-step
    writes stay inside one method so the commit boundary is visible in one
    place. Deliberate extra commits (e.g. "never roll back the order because a
    side record failed") are allowed *inside* the Action, with a comment.
    """

    model: type[TModel]

    async def save(self, obj: TModel) -> TModel:
        """add + commit + refresh — the common tail of a create command."""
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def commit_and_refresh(self, obj: TModel) -> TModel:
        """Commit in-place mutations of an already-loaded row."""
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: TModel) -> None:
        await self.db.delete(obj)
        await self.db.commit()
