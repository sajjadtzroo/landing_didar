import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    status: str  # pending | running | done | failed
    total: int
    processed: int
    created_count: int
    updated_count: int
    errors: list | None = None
    result: dict | None = None
    created_at: datetime
