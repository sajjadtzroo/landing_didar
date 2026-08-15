from app.domains.chat.routers.account import router as account_router
from app.domains.chat.routers.admin import router as admin_router
from app.domains.chat.routers.ws import router as ws_router

__all__ = ["account_router", "admin_router", "ws_router"]
