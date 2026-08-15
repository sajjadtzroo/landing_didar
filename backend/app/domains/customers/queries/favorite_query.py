import uuid

from sqlalchemy import select

# catalog sits below customers in the domain DAG — public-API import is fine.
from app.domains.catalog import Product
from app.domains.customers.models import Favorite
from app.shared.cqrs import BaseQuery


class FavoriteQuery(BaseQuery[Favorite]):
    model = Favorite

    async def products_for(self, customer_id: uuid.UUID) -> list[Product]:
        """The customer's wishlist as live products, most recently added first."""
        rows = await self.db.execute(
            select(Product)
            .join(Favorite, Favorite.product_id == Product.id)
            .where(Favorite.customer_id == customer_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(rows.scalars().all())
