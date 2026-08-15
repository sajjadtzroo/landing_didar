from app.domains.users.routers.admin_audit import router as admin_audit_router
from app.domains.users.routers.admin_users import router as admin_users_router
from app.domains.users.routers.auth import router as auth_router

__all__ = ["admin_audit_router", "admin_users_router", "auth_router"]
