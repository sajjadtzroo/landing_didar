from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GoldPriceSnapshot(Base):
    """Last-good gold-price board persisted so the panel survives restarts and
    TGJU outages. Single row (id=1), upserted on every successful scrape."""

    __tablename__ = "gold_price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tgju")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
