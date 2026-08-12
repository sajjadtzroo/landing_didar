# DEPRECATED aggregator: models are moving to app/domains/<domain>/;
# this re-export shim keeps old import paths working until the final
# cleanup step of the migration. remove in step 10.
from app.domains.content.models import FAQ, Landing, Portfolio
from app.domains.pricing.models import GoldPriceSnapshot
from app.domains.users.models import AdminRole, AuditLog, User
from app.models.agent import AgentRetailer, AgentVisit, MobileGalleryItem
from app.models.customer import Customer, CustomerAddress, Favorite, OtpCode
from app.models.import_job import ImportJob
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusLog
from app.models.product import Product
from app.models.product_serial import ProductSerial, ProductSerialStatus, SerialScan
from app.models.warranty import BuybackRequest, BuybackStatus, Warranty

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
