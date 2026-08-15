from app.domains.serials.routers.admin import router as admin_router
from app.domains.serials.routers.admin_buybacks import router as admin_buybacks_router
from app.domains.serials.routers.public import router as public_router

__all__ = ["admin_buybacks_router", "admin_router", "public_router"]
