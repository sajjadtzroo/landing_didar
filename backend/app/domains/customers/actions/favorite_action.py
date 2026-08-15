import uuid

from fastapi import HTTPException
from sqlalchemy import delete

# catalog sits below customers in the domain DAG — public-API import is fine.
from app.domains.catalog import Product
from app.domains.customers.models import Favorite
from app.shared.cqrs import BaseAction


class FavoriteAction(BaseAction[Favorite]):
    model = Favorite

    async def add(self, customer_id: uuid.UUID, product_id: uuid.UUID) -> None:
        """Idempotent add: the composite PK prevents dupes, a repeat is a no-op."""
        if await self.db.get(Product, product_id) is None:
            raise HTTPException(404, detail="Product not found")
        exists = await self.db.get(
            Favorite, {"customer_id": customer_id, "product_id": product_id}
        )
        if exists is None:
            self.db.add(Favorite(customer_id=customer_id, product_id=product_id))
            await self.db.commit()

    async def remove(self, customer_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(Favorite).where(
                Favorite.customer_id == customer_id, Favorite.product_id == product_id
            )
        )
        await self.db.commit()
