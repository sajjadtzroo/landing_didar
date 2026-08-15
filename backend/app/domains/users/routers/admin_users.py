import uuid

from fastapi import APIRouter, Depends, Request

from app.core.security import SESSION_COOKIE, read_session
from app.domains.users.actions import UserAction
from app.domains.users.dependencies import require_superadmin
from app.domains.users.queries import UserQuery
from app.domains.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(dependencies=[Depends(require_superadmin)])


def _me(request: Request) -> str | None:
    return read_session(request.cookies.get(SESSION_COOKIE))


@router.get("/users", response_model=list[UserOut])
async def list_users(users: UserQuery = Depends()):
    return await users.list_all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, action: UserAction = Depends()):
    return await action.create(payload)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    users: UserQuery = Depends(),
    action: UserAction = Depends(),
):
    user = await users.by_id_or_404(user_id, detail="User not found")
    return await action.update_admin(user, payload, me=_me(request))


@router.get("/users/{user_id}/retailers", response_model=list[uuid.UUID])
async def get_user_retailers(user_id: uuid.UUID, users: UserQuery = Depends()):
    """Customer ids assigned to this agent (WO 7.5 assignment)."""
    return await users.retailer_ids(user_id)


@router.put("/users/{user_id}/retailers", response_model=list[uuid.UUID])
async def set_user_retailers(
    user_id: uuid.UUID,
    customer_ids: list[uuid.UUID],
    users: UserQuery = Depends(),
    action: UserAction = Depends(),
):
    """Replace the agent's retailer assignment with the given customer ids."""
    user = await users.by_id_or_404(user_id, detail="User not found")
    return await action.set_retailers(user, customer_ids)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    users: UserQuery = Depends(),
    action: UserAction = Depends(),
):
    user = await users.by_id_or_404(user_id, detail="User not found")
    await action.delete_admin(user, me=_me(request))
