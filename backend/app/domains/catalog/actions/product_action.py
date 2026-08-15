from app.domains.catalog.models import Product
from app.domains.catalog.schemas import ProductCreate, ProductUpdate
from app.domains.catalog.services.cache import bust_products_cache
from app.shared.cqrs import BaseAction


class ProductAction(BaseAction[Product]):
    model = Product

    async def create(self, payload: ProductCreate) -> Product:
        product = await self.save(Product(**payload.model_dump()))
        await bust_products_cache()
        return product

    async def update(self, product: Product, payload: ProductUpdate) -> Product:
        """Admin PATCH: partial update — only fields the client sent."""
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(product, k, v)
        product = await self.commit_and_refresh(product)
        await bust_products_cache()
        return product

    async def set_image(self, product: Product, url: str) -> Product:
        """Record an already-stored upload as the product's main image."""
        product.image_url = url
        product = await self.commit_and_refresh(product)
        await bust_products_cache()
        return product

    async def delete(self, product: Product) -> None:
        await super().delete(product)
        await bust_products_cache()
