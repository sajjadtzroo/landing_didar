from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

_DEFAULT: dict = {"price_requires_login": False}


class SiteSettings(Base):
    """Singleton settings row (id=1). Access via get_or_create() helpers in the
    router — never instantiate directly with a different id."""

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=_DEFAULT)

    @property
    def price_requires_login(self) -> bool:
        return bool((self.data or {}).get("price_requires_login", False))
