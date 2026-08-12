"""Users domain: panel users, roles, auth resolution, audit log.

PUBLIC API — the only surface other code may import from."""

from app.domains.users.dependencies import (
    AdminUser,
    require_admin,
    require_agent,
    require_superadmin,
    resolve_admin,
)
from app.domains.users.models import AdminRole, AuditLog, User

__all__ = [
    "AdminRole",
    "AdminUser",
    "AuditLog",
    "User",
    "require_admin",
    "require_agent",
    "require_superadmin",
    "resolve_admin",
]
