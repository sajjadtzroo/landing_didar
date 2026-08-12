from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.content_defaults import default_content
from app.core.db import get_db
from app.domains.content.models import Landing
from app.domains.content.schemas import LandingAdminOut, LandingCreate, LandingUpdate
from app.domains.content.service import bust_landing_cache

router = APIRouter(dependencies=[Depends(require_admin)])


def _admin_out(landing: Landing) -> LandingAdminOut:
    return LandingAdminOut.model_validate(landing)


async def _get_or_404(db: AsyncSession, landing_id: str) -> Landing:
    landing = await db.get(Landing, landing_id)
    if landing is None:
        raise HTTPException(404, detail="Landing not found")
    return landing


@router.get("/landings", response_model=list[LandingAdminOut])
async def list_landings(db: AsyncSession = Depends(get_db)):
    landings = (
        await db.execute(select(Landing).order_by(Landing.slug))
    ).scalars().all()
    return [_admin_out(ln) for ln in landings]


@router.post("/landings", response_model=LandingAdminOut, status_code=201)
async def create_landing(payload: LandingCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(Landing.id).where(Landing.slug == payload.slug))
    if exists:
        raise HTTPException(409, detail="A landing with this slug already exists")
    landing = Landing(
        slug=payload.slug, title=payload.title, content=default_content()
    )
    db.add(landing)
    await db.commit()
    await db.refresh(landing)
    return _admin_out(landing)


@router.get("/landings/{landing_id}", response_model=LandingAdminOut)
async def get_landing(landing_id: str, db: AsyncSession = Depends(get_db)):
    return _admin_out(await _get_or_404(db, landing_id))


@router.patch("/landings/{landing_id}", response_model=LandingAdminOut)
async def update_landing(
    landing_id: str, payload: LandingUpdate, db: AsyncSession = Depends(get_db)
):
    landing = await _get_or_404(db, landing_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(landing, k, v)
    await db.commit()
    await db.refresh(landing)
    await bust_landing_cache(landing.slug)
    return _admin_out(landing)


@router.delete("/landings/{landing_id}", status_code=204)
async def delete_landing(landing_id: str, db: AsyncSession = Depends(get_db)):
    landing = await _get_or_404(db, landing_id)
    slug = landing.slug
    await db.delete(landing)
    await db.commit()
    await bust_landing_cache(slug)
