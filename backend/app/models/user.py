import enum
import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AdminRole(enum.StrEnum):
    """WO 7.15 role set. superadmin/operator use the admin panel today;
    retailer/agent/support accounts exist now and get their flows in Phase 5."""

    superadmin = "superadmin"
    operator = "operator"
    retailer = "retailer"
    agent = "agent"
    support = "support"


class User(Base):
    """Named platform user. The env-var admin remains a zero-config bootstrap
    superadmin outside this table; everyone else lives here."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, name="admin_role"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    """One row per mutating admin request (middleware) + auth events. `actor`
    is the username string (works for the env bootstrap admin, survives user
    deletion)."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)  # "METHOD /path"
    status: Mapped[int | None] = mapped_column(Integer)  # response status code
    meta: Mapped[dict | None] = mapped_column(JSONB)
