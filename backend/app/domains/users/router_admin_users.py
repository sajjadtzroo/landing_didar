import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import SESSION_COOKIE, hash_password_async, read_session
from app.domains.users.dependencies import require_superadmin
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(dependencies=[Depends(require_superadmin)])


def _me(request: Request) -> str | None:
    return read_session(request.cookies.get(SESSION_COOKIE))


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(User).order_by(User.created_at))
    return rows.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(
        username=payload.username,
        password_hash=await hash_password_async(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, detail="Username already exists")
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    # A superadmin can't lock themselves out.
    if user.username == _me(request) and data.get("is_active") is False:
        raise HTTPException(400, detail="Cannot deactivate yourself")
    if user.username == _me(request) and "role" in data:
        raise HTTPException(400, detail="Cannot change your own role")
    if "password" in data:
        user.password_hash = await hash_password_async(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}/retailers", response_model=list[uuid.UUID])
async def get_user_retailers(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Customer ids assigned to this agent (WO 7.5 assignment)."""
    from app.domains.agents import AgentRetailer

    rows = await db.execute(
        select(AgentRetailer.customer_id).where(AgentRetailer.agent_id == user_id)
    )
    return list(rows.scalars().all())


@router.put("/users/{user_id}/retailers", response_model=list[uuid.UUID])
async def set_user_retailers(
    user_id: uuid.UUID, customer_ids: list[uuid.UUID], db: AsyncSession = Depends(get_db)
):
    """Replace the agent's retailer assignment with the given customer ids."""
    from sqlalchemy import delete

    from app.domains.agents import AgentRetailer

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    await db.execute(delete(AgentRetailer).where(AgentRetailer.agent_id == user_id))
    for cid in set(customer_ids):
        db.add(AgentRetailer(agent_id=user_id, customer_id=cid))
    await db.commit()
    return list(set(customer_ids))


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    if user.username == _me(request):
        raise HTTPException(400, detail="Cannot delete yourself")
    await db.delete(user)
    await db.commit()
