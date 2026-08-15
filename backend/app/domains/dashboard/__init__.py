"""Dashboard domain: read-only cross-domain KPI aggregation for the admin panel.

PUBLIC API — the only surface other code may import from."""

from app.domains.dashboard.queries import DashboardQuery

__all__ = ["DashboardQuery"]
