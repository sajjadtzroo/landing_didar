# DEPRECATED aggregator: models are moving to app/domains/<domain>/;
# this re-export shim keeps old import paths working until the final
# cleanup step of the migration. remove in step 10.
from app.domains.catalog.models import ImportJob, Product
from app.domains.content.models import FAQ, Landing, Portfolio
from app.domains.pricing.models import GoldPriceSnapshot
from app.domains.users.models import AdminRole, AuditLog, User
from app.domains.agents.models import AgentRetailer, AgentVisit, MobileGalleryItem
from app.domains.customers.models import Customer, CustomerAddress, Favorite, OtpCode
from app.domains.orders.models import Order, OrderItem, OrderStatus, OrderStatusLog
from app.domains.serials.serial_models import ProductSerial, ProductSerialStatus, SerialScan
from app.domains.serials.warranty_models import BuybackRequest, BuybackStatus, Warranty

__all__ = [
    "Product",
    "ImportJob",
    "Warranty",
    "BuybackRequest",
    "BuybackStatus",
    "AgentRetailer",
    "AgentVisit",
    "MobileGalleryItem",
    "User",
    "AdminRole",
    "AuditLog",
    "FAQ",
    "GoldPriceSnapshot",
    "Landing",
    "Portfolio",
    "ProductSerial",
    "ProductSerialStatus",
    "SerialScan",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderStatusLog",
    "Customer",
    "CustomerAddress",
    "Favorite",
    "OtpCode",
]
