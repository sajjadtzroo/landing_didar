from typing import ClassVar

from sqlalchemy import func, select

from app.domains.catalog.models import Product
from app.shared.cqrs import BaseQuery


class ProductQuery(BaseQuery[Product]):
    model = Product

    # Storefront visibility: active AND actually sellable/displayable.
    _ACTIVE: ClassVar = (Product.is_active, Product.product_status != "not_for_sale")

    async def admin_list(self) -> list[Product]:
        """Every product (any status), in the admin's manual sort order."""
        return await self.all(self.stmt().order_by(Product.sort_order))

    async def active_page(
        self, *, page: int | None, page_size: int
    ) -> tuple[list[Product], int]:
        """Active catalog, ordered. ``page=None`` returns the full list (total =
        its length — existing storefront contract); with ``page``, a slice of
        ``page_size`` plus the active total."""
        stmt = (
            self.stmt()
            .where(*self._ACTIVE)
            # secondary key makes page boundaries deterministic on sort_order ties
            .order_by(Product.sort_order, Product.id)
        )
        if page is None:
            rows = await self.all(stmt)
            return rows, len(rows)
        total = await self.db.scalar(
            select(func.count()).select_from(Product).where(*self._ACTIVE)
        )
        rows = await self.all(stmt.offset((page - 1) * page_size).limit(page_size))
        return rows, total or 0

    async def active_by_slug(self, slug: str) -> Product | None:
        return await self.one_or_none(
            self.stmt().where(Product.slug == slug, *self._ACTIVE)
        )
