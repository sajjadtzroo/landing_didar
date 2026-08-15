"""Admin FAQ CRUD.

Split verbatim from app/api/v1/admin_catalog.py during the domain migration;
registered with the same prefix and tags=["admin:catalog"] so the OpenAPI
contract is unchanged."""

from fastapi import APIRouter, Depends

from app.domains.content.actions import FaqAction
from app.domains.content.queries import FaqQuery
from app.domains.content.schemas import FAQCreate, FAQOut, FAQUpdate
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(faqs: FaqQuery = Depends()):
    return await faqs.list_admin()


@router.post("/faqs", response_model=FAQOut, status_code=201)
async def create_faq(payload: FAQCreate, action: FaqAction = Depends()):
    return await action.create(payload)


@router.patch("/faqs/{faq_id}", response_model=FAQOut)
async def update_faq(
    faq_id: str,
    payload: FAQUpdate,
    faqs: FaqQuery = Depends(),
    action: FaqAction = Depends(),
):
    faq = await faqs.by_id_or_404(faq_id, detail="FAQ not found")
    return await action.update(faq, payload)


@router.delete("/faqs/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: str, faqs: FaqQuery = Depends(), action: FaqAction = Depends()
):
    faq = await faqs.by_id_or_404(faq_id, detail="FAQ not found")
    await action.delete(faq)
