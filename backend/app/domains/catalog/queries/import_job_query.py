from app.domains.catalog.models import ImportJob
from app.shared.cqrs import BaseQuery


class ImportJobQuery(BaseQuery[ImportJob]):
    """Read side for import jobs — the admin UI polls `by_id_or_404`."""

    model = ImportJob
