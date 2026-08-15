import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password_async, verify_password_async
from app.domains.users.models import AuditLog, User
from app.domains.users.queries import UserQuery
from app.domains.users.schemas import UserCreate, UserUpdate
from app.shared.cqrs import BaseAction

# agents' public API itself imports users (allowed by the DAG — users is the
# bottom layer), so importing agents at module scope here would make
# users.__init__ circular — set_retailers below imports lazily instead.


class UserAction(BaseAction[User]):
    model = User

    async def login(self, username: str, password: str) -> str | None:
        """Credentials -> role string, or None when invalid. Named users first;
        the env-var admin resolves as the zero-config bootstrap superadmin.
        Both outcomes are audited here — login is the one mutation the audit
        middleware can't attribute (there's no cookie yet)."""
        role = None
        user = await UserQuery(self.db).active_by_username(username)
        if user is not None and await verify_password_async(
            password, user.password_hash
        ):
            role = user.role.value
        elif username == settings.admin_username and await verify_password_async(
            password, settings.admin_password_hash
        ):
            role = "superadmin"

        self.db.add(
            AuditLog(
                actor=username[:60],
                action="auth.login",
                status=200 if role else 401,
            )
        )
        await self.db.commit()
        return role

    async def create(self, payload: UserCreate) -> User:
        user = User(
            username=payload.username,
            password_hash=await hash_password_async(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            role=payload.role,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, detail="Username already exists") from None
        await self.db.refresh(user)
        return user

    async def update_admin(
        self, user: User, payload: UserUpdate, *, me: str | None
    ) -> User:
        data = payload.model_dump(exclude_unset=True)
        # A superadmin can't lock themselves out.
        if user.username == me and data.get("is_active") is False:
            raise HTTPException(400, detail="Cannot deactivate yourself")
        if user.username == me and "role" in data:
            raise HTTPException(400, detail="Cannot change your own role")
        if "password" in data:
            user.password_hash = await hash_password_async(data.pop("password"))
        for k, v in data.items():
            setattr(user, k, v)
        return await self.commit_and_refresh(user)

    async def set_retailers(
        self, user: User, customer_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Replace the agent's retailer assignment with the given customer ids."""
        from sqlalchemy import delete

        from app.domains.agents import AgentRetailer  # lazy — see module comment

        await self.db.execute(
            delete(AgentRetailer).where(AgentRetailer.agent_id == user.id)
        )
        for cid in set(customer_ids):
            self.db.add(AgentRetailer(agent_id=user.id, customer_id=cid))
        await self.db.commit()
        return list(set(customer_ids))

    async def delete_admin(self, user: User, *, me: str | None) -> None:
        if user.username == me:
            raise HTTPException(400, detail="Cannot delete yourself")
        await self.delete(user)
