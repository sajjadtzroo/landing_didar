"""Business domains (modular monolith).

Each subpackage is a self-contained domain. Its ``__init__`` is the ONLY
legal import surface for other domains (enforced by import-linter).

Importing this package imports every domain's ``models`` module so all
SQLAlchemy mappers register on ``Base.metadata`` — Alembic's env.py and the
app factory both rely on that.
"""

from app.domains.content import models as _content_models  # noqa: F401
from app.domains.pricing import models as _pricing_models  # noqa: F401
from app.domains.users import models as _users_models  # noqa: F401
