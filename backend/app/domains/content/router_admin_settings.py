import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.core.db import get_db
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class SettingsOut(BaseModel):
    price_requires_login: bool


class SettingsPatch(BaseModel):
    price_requires_login: bool


async def _read(db: AsyncSession) -> bool:
    result = await db.execute(text("SELECT data FROM site_settings WHERE id = 1"))
    row = result.scalar_one_or_none()
    if row:
        return bool(row.get("price_requires_login", False))
    return False


@router.get("/settings", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return SettingsOut(price_requires_login=await _read(db))


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(
    payload: SettingsPatch, db: AsyncSession = Depends(get_db)
):
    await db.execute(
        text("""
            INSERT INTO site_settings (id, data)
            VALUES (1, :data::jsonb)
            ON CONFLICT (id) DO UPDATE
              SET data = EXCLUDED.data
        """),
        {"data": json.dumps({"price_requires_login": payload.price_requires_login})},
    )
    await db.commit()
    await cache_delete("cache:site_settings")
    value = await _read(db)
    return SettingsOut(price_requires_login=value)
