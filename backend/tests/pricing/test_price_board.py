"""PriceAction.upsert_board / PriceQuery.last_board — the persisted last-good
gold board (single row, id=1). Constructed directly with a test session, the
documented out-of-request usage (see app/shared/cqrs.py)."""

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text

from app.domains.pricing.actions import PriceAction
from app.domains.pricing.models import GoldPriceSnapshot
from app.domains.pricing.queries import PriceQuery

pytestmark = pytest.mark.asyncio(loop_scope="session")

_ITEMS = [
    {"symbol": "geram18", "label": "طلای ۱۸ عیار (هر گرم)", "unit": "toman",
     "price": 18_904_800, "change_pct": 1.76, "direction": "high",
     "updated_at": "۱۵:۲۷:۲۹"},
    {"symbol": "ons", "label": "انس طلا", "unit": "usd", "price": 4343.43,
     "change_pct": 0.14, "direction": "high", "updated_at": "۱۵:۲۷:۲۹"},
]


@pytest_asyncio.fixture(autouse=True)
async def _clean_snapshots(_sessionmaker):
    """gold_price_snapshots is not in conftest's TRUNCATE list — clear it here."""
    async with _sessionmaker() as s:
        await s.execute(text("DELETE FROM gold_price_snapshots"))
        await s.commit()
    yield


async def test_last_board_none_before_first_upsert(_sessionmaker):
    async with _sessionmaker() as s:
        assert await PriceQuery(s).last_board() is None


async def test_upsert_then_last_board_roundtrip(_sessionmaker):
    async with _sessionmaker() as s:
        await PriceAction(s).upsert_board(_ITEMS)
    async with _sessionmaker() as s:  # fresh session — must come from the DB
        row = await PriceQuery(s).last_board()
    assert row is not None and row.id == 1
    assert row.items == _ITEMS  # JSONB round-trips the full board verbatim
    assert row.source == "tgju"
    assert row.fetched_at is not None and row.fetched_at.tzinfo is not None


async def test_upsert_overwrites_the_single_row(_sessionmaker):
    async with _sessionmaker() as s:
        await PriceAction(s).upsert_board(_ITEMS)
        first = (await PriceQuery(s).last_board()).fetched_at
    newer = [dict(_ITEMS[0], price=19_000_000)]
    async with _sessionmaker() as s:
        await PriceAction(s).upsert_board(newer, source="manual")
        n = await s.scalar(select(func.count()).select_from(GoldPriceSnapshot))
        row = await PriceQuery(s).last_board()
    assert n == 1  # upsert, never a second row
    assert row.items == newer
    assert row.source == "manual"
    assert row.fetched_at >= first
