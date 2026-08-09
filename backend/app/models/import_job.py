import uuid

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ImportJob(Base):
    """A background bulk job (CSV product import / MinIO photo sync) the admin
    UI polls for progress. ponytail: BackgroundTasks + this row is the whole
    queue — swap in a real broker only if imports outgrow one process."""

    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # products_csv | image_sync
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending", nullable=False
    )  # pending | running | done | failed
    actor: Mapped[str | None] = mapped_column(String(60))
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # [{row: int, error: str}] — bad rows are reported, good rows still land.
    errors: Mapped[list | None] = mapped_column(JSONB, default=list)
    result: Mapped[dict | None] = mapped_column(JSONB)
