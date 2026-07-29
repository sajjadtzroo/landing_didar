import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.landing import Landing, LandingProduct
from app.models.product import Product
from app.schemas.landing import LandingAdminOut, LandingProductsSet, LandingUpdate

router = APIRouter(dependencies=[Depends(require_admin)])


async def _product_ids(db: AsyncSession, landing_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await db.execute(
        select(LandingProduct.product_id)
        .where(LandingProduct.landing_id == landing_id)
        .order_by(LandingProduct.sort_order)
    )
    return list(rows.scalars().all())


async def _admin_out(db: AsyncSession, landing: Landing) -> LandingAdminOut:
    return LandingAdminOut(
        id=landing.id,
        slug=landing.slug,
        title=landing.title,
        hero_video_url=landing.hero_video_url,
        hero_poster_url=landing.hero_poster_url,
        product_ids=await _product_ids(db, landing.id),
    )


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
    return [await _admin_out(db, ln) for ln in landings]


@router.get("/landings/{landing_id}", response_model=LandingAdminOut)
async def get_landing(landing_id: str, db: AsyncSession = Depends(get_db)):
    return await _admin_out(db, await _get_or_404(db, landing_id))


@router.patch("/landings/{landing_id}", response_model=LandingAdminOut)
async def update_landing(
    landing_id: str, payload: LandingUpdate, db: AsyncSession = Depends(get_db)
):
    landing = await _get_or_404(db, landing_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(landing, k, v)
    await db.commit()
    await db.refresh(landing)
    return await _admin_out(db, landing)


@router.put("/landings/{landing_id}/products", response_model=LandingAdminOut)
async def set_landing_products(
    landing_id: str, payload: LandingProductsSet, db: AsyncSession = Depends(get_db)
):
    landing = await _get_or_404(db, landing_id)

    # De-dupe preserving order (composite PK forbids repeats).
    ids: list[uuid.UUID] = list(dict.fromkeys(payload.product_ids))
    if ids:
        found = set(
            (await db.execute(select(Product.id).where(Product.id.in_(ids)))).scalars()
        )
        missing = [str(i) for i in ids if i not in found]
        if missing:
            raise HTTPException(
                422, detail=f"Unknown product ids: {', '.join(missing)}"
            )

    # Replace the whole assignment; sort_order = position in the list.
    await db.execute(
        delete(LandingProduct).where(LandingProduct.landing_id == landing.id)
    )
    db.add_all(
        LandingProduct(landing_id=landing.id, product_id=pid, sort_order=i)
        for i, pid in enumerate(ids)
    )
    await db.commit()
    return await _admin_out(db, landing)
