from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.core.db import get_db
from app.domains.content.models import SiteSettings
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class SettingsOut(BaseModel):
    price_requires_login: bool


class SettingsPatch(BaseModel):
    price_requires_login: bool


async def _get_or_create(db: AsyncSession) -> SiteSettings:
    row = await db.get(SiteSettings, 1)
    if row is None:
        row = SiteSettings(id=1, data={"price_requires_login": False})
        db.add(row)
        await db.flush()
    return row


@router.get("/settings", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db)
    return SettingsOut(price_requires_login=row.price_requires_login)


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(
    payload: SettingsPatch, db: AsyncSession = Depends(get_db)
):
    row = await _get_or_create(db)
    row.data = {**(row.data or {}), "price_requires_login": payload.price_requires_login}
    await db.commit()
    await db.refresh(row)
    await cache_delete("cache:site_settings")
    return SettingsOut(price_requires_login=row.price_requires_login)
