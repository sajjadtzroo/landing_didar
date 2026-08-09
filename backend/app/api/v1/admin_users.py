import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_superadmin
from app.core.db import get_db
from app.core.security import hash_password, read_session
from app.core.security import SESSION_COOKIE
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate

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
        password_hash=hash_password(payload.password),
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
        user.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


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
