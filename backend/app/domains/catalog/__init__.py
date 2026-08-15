"""Catalog domain: products, bulk CSV import, MinIO image sync.

PUBLIC API — the only surface other code may import from."""

from app.domains.catalog.actions import ImportJobAction, ProductAction
from app.domains.catalog.models import ImportJob, Product
from app.domains.catalog.queries import ImportJobQuery, ProductQuery
from app.domains.catalog.schemas import ProductOut

__all__ = [
    "ImportJob",
    "ImportJobAction",
    "ImportJobQuery",
    "Product",
    "ProductAction",
    "ProductOut",
    "ProductQuery",
]
