from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domains.pricing.models import GoldPriceSnapshot
from app.shared.cqrs import BaseAction


class PriceAction(BaseAction[GoldPriceSnapshot]):
    """Write side of the price board: upsert of the single last-good row."""

    model = GoldPriceSnapshot

    async def upsert_board(self, items: list[dict], source: str = "tgju") -> None:
        """Upsert the single last-good row (id=1) with the freshly scraped board."""
        stmt = pg_insert(GoldPriceSnapshot).values(
            id=1, items=items, source=source, fetched_at=datetime.now(UTC)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            # subscript access: the column is named "items", which shadows the
            # ColumnCollection.items() method under attribute access.
            set_={
                "items": stmt.excluded["items"],
                "source": stmt.excluded["source"],
                "fetched_at": stmt.excluded["fetched_at"],
                "updated_at": datetime.now(UTC),
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()
