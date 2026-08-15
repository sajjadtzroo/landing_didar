from app.domains.catalog.models import ImportJob
from app.shared.cqrs import BaseAction


class ImportJobAction(BaseAction[ImportJob]):
    """Creates the pollable job rows for the bulk-import background workers.

    Only the request-time commit lives here; the workers themselves
    (`services/import_service.py`) run after the response and own their own
    sessions/commits — the request session is long gone by then."""

    model = ImportJob

    async def start_products_import(
        self, rows: list[dict], parse_errors: list[dict]
    ) -> ImportJob:
        return await self.save(
            ImportJob(
                kind="products_csv",
                status="running",
                total=len(rows),
                errors=parse_errors,
            )
        )

    async def start_image_sync(self) -> ImportJob:
        return await self.save(ImportJob(kind="image_sync", status="running"))
