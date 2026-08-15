from app.domains.pricing.models import GoldPriceSnapshot
from app.shared.cqrs import BaseQuery


class PriceQuery(BaseQuery[GoldPriceSnapshot]):
    """Read side of the price board: the single persisted last-good snapshot."""

    model = GoldPriceSnapshot

    async def last_board(self) -> GoldPriceSnapshot | None:
        """The one snapshot row (id=1), or None before the first good scrape."""
        return await self.by_id(1)
