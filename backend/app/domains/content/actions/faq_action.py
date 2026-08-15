from app.domains.content.models import FAQ
from app.domains.content.schemas import FAQCreate, FAQUpdate
from app.shared.cqrs import BaseAction


class FaqAction(BaseAction[FAQ]):
    model = FAQ

    async def create(self, payload: FAQCreate) -> FAQ:
        return await self.save(FAQ(**payload.model_dump()))

    async def update(self, faq: FAQ, payload: FAQUpdate) -> FAQ:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(faq, k, v)
        return await self.commit_and_refresh(faq)
