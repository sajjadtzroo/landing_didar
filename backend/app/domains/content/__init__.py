"""Content domain: admin-curated landings, portfolios and FAQs.

This module is the domain's PUBLIC API — the only surface other code may
import from (enforced by import-linter)."""

from app.domains.content.models import FAQ, Landing, Portfolio

# Routers are intentionally NOT imported here: they pull in FastAPI dependency
# modules and would make importing a model drag in the HTTP stack (and cycle).
# main.py — the composition root — registers them via direct submodule imports.
__all__ = ["FAQ", "Landing", "Portfolio"]
