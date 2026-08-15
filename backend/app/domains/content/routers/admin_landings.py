"""Admin landing CRUD — thin HTTP layer over LandingQuery / LandingAction."""

from fastapi import APIRouter, Depends

from app.domains.content.actions import LandingAction
from app.domains.content.models import Landing
from app.domains.content.queries import LandingQuery
from app.domains.content.schemas import LandingAdminOut, LandingCreate, LandingUpdate
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


def _admin_out(landing: Landing) -> LandingAdminOut:
    return LandingAdminOut.model_validate(landing)


@router.get("/landings", response_model=list[LandingAdminOut])
async def list_landings(landings: LandingQuery = Depends()):
    return [_admin_out(ln) for ln in await landings.list_admin()]


@router.post("/landings", response_model=LandingAdminOut, status_code=201)
async def create_landing(payload: LandingCreate, action: LandingAction = Depends()):
    return _admin_out(await action.create(payload))


@router.get("/landings/{landing_id}", response_model=LandingAdminOut)
async def get_landing(landing_id: str, landings: LandingQuery = Depends()):
    return _admin_out(
        await landings.by_id_or_404(landing_id, detail="Landing not found")
    )


@router.patch("/landings/{landing_id}", response_model=LandingAdminOut)
async def update_landing(
    landing_id: str,
    payload: LandingUpdate,
    landings: LandingQuery = Depends(),
    action: LandingAction = Depends(),
):
    landing = await landings.by_id_or_404(landing_id, detail="Landing not found")
    return _admin_out(await action.update(landing, payload))


@router.delete("/landings/{landing_id}", status_code=204)
async def delete_landing(
    landing_id: str,
    landings: LandingQuery = Depends(),
    action: LandingAction = Depends(),
):
    landing = await landings.by_id_or_404(landing_id, detail="Landing not found")
    await action.delete(landing)
