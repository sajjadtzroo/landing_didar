from app.domains.customers.routers.account import router as account_router
from app.domains.customers.routers.admin import router as admin_router

__all__ = ["account_router", "admin_router"]
