"""Business domains (modular monolith).

Each subpackage is a self-contained domain. Its ``__init__`` is the ONLY
legal import surface for other domains (enforced by import-linter).

Importing this package imports every domain's ``models`` module so all
SQLAlchemy mappers register on ``Base.metadata`` — Alembic's env.py and the
app factory both rely on that.
"""

from app.domains.catalog import models as _catalog_models  # noqa: F401
from app.domains.content import models as _content_models  # noqa: F401
from app.domains.customers import models as _customers_models  # noqa: F401
from app.domains.orders import models as _orders_models  # noqa: F401
from app.domains.pricing import models as _pricing_models  # noqa: F401
from app.domains.serials import serial_models as _serial_models  # noqa: F401
from app.domains.serials import warranty_models as _warranty_models  # noqa: F401
from app.domains.users import models as _users_models  # noqa: F401
