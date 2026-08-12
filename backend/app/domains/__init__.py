"""Business domains (modular monolith).

Each subpackage is a self-contained domain. Its ``__init__`` is the ONLY
legal import surface for other domains (enforced by import-linter).

Importing this package imports every domain's ``models`` module so all
SQLAlchemy mappers register on ``Base.metadata`` — Alembic's env.py and the
app factory both rely on that.
"""
