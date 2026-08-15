from app.domains.content.models import FAQ
from app.shared.cqrs import BaseQuery


class FaqQuery(BaseQuery[FAQ]):
    model = FAQ

    async def list_public(self) -> list[FAQ]:
        return await self.all(
            self.stmt().where(FAQ.is_active).order_by(FAQ.sort_order)
        )

    async def list_admin(self) -> list[FAQ]:
        return await self.all(self.stmt().order_by(FAQ.sort_order))
