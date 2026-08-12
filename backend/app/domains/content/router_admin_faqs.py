"""Admin FAQ CRUD.

Split verbatim from app/api/v1/admin_catalog.py during the domain migration;
registered with the same prefix and tags=["admin:catalog"] so the OpenAPI
contract is unchanged."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.domains.content.models import FAQ
from app.domains.content.schemas import FAQCreate, FAQOut, FAQUpdate
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FAQ).order_by(FAQ.sort_order))
    return res.scalars().all()


@router.post("/faqs", response_model=FAQOut, status_code=201)
async def create_faq(payload: FAQCreate, db: AsyncSession = Depends(get_db)):
    faq = FAQ(**payload.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


@router.patch("/faqs/{faq_id}", response_model=FAQOut)
async def update_faq(
    faq_id: str, payload: FAQUpdate, db: AsyncSession = Depends(get_db)
):
    faq = await db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(404, detail="FAQ not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(faq, k, v)
    await db.commit()
    await db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}", status_code=204)
async def delete_faq(faq_id: str, db: AsyncSession = Depends(get_db)):
    faq = await db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(404, detail="FAQ not found")
    await db.delete(faq)
    await db.commit()
