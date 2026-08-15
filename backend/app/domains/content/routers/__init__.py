from app.domains.content.routers.admin_faqs import router as admin_faqs_router
from app.domains.content.routers.admin_landings import router as admin_landings_router
from app.domains.content.routers.admin_portfolios import (
    router as admin_portfolios_router,
)
from app.domains.content.routers.public import router as public_router

__all__ = [
    "admin_faqs_router",
    "admin_landings_router",
    "admin_portfolios_router",
    "public_router",
]
