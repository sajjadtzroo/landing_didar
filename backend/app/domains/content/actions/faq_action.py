from app.core.cache import cache_delete
from app.domains.content.models import FAQ
from app.domains.content.schemas import FAQCreate, FAQUpdate
from app.shared.cqrs import BaseAction

_FAQS_CACHE_KEY = "cache:faqs"


class FaqAction(BaseAction[FAQ]):
    model = FAQ

    async def create(self, payload: FAQCreate) -> FAQ:
        faq = await self.save(FAQ(**payload.model_dump()))
        await cache_delete(_FAQS_CACHE_KEY)
        return faq

    async def update(self, faq: FAQ, payload: FAQUpdate) -> FAQ:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(faq, k, v)
        faq = await self.commit_and_refresh(faq)
        await cache_delete(_FAQS_CACHE_KEY)
        return faq

    async def delete(self, faq: FAQ) -> None:
        await super().delete(faq)
        await cache_delete(_FAQS_CACHE_KEY)
