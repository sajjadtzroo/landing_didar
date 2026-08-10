from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

# 2 gunicorn workers × (10 + 10 overflow) = 40 max conns — well under PG's 100.
engine = create_async_engine(
    settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=10
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# --- slow-query logging (db.query namespace, SLOW_QUERY_MS threshold) -----------
if settings.slow_query_ms > 0:
    import time as _time

    from sqlalchemy import event

    from app.core.logging import get_logger

    _qlog = get_logger("db.query")

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _q_start(conn, cursor, statement, parameters, context, executemany):
        context._query_start = _time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _q_end(conn, cursor, statement, parameters, context, executemany):
        ms = (_time.perf_counter() - getattr(context, "_query_start", _time.perf_counter())) * 1000
        if ms >= settings.slow_query_ms:
            from app.core.metrics import SLOW_QUERIES

            SLOW_QUERIES.inc()
            _qlog.bind(event="db.query.slow", duration_ms=round(ms, 1)).warning(
                "slow query ({} ms): {}", round(ms, 1), statement[:500]
            )


class Base(DeclarativeBase):
    """created_at / updated_at on every row (TIMESTAMPTZ)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
