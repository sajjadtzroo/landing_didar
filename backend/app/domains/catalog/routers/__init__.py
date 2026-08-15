from app.domains.catalog.routers.admin import router as admin_router
from app.domains.catalog.routers.public import router as public_router

__all__ = ["admin_router", "public_router"]
