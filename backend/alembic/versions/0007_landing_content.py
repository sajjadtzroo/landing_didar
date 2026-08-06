"""landing content JSONB + backfill per-section content

Adds landings.content (JSONB). Backfills existing landings so they render
identically after deploy: content = standard defaults, product groups derived
from each landing's current landing_products split by product.category.
landing_products is left in place (no longer read).

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-06
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.content_defaults import default_content, groups_from_category_rows

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "landings", sa.Column("content", postgresql.JSONB(), nullable=True)
    )

    bind = op.get_bind()
    landings = bind.execute(sa.text("SELECT id FROM landings")).fetchall()
    for (lid,) in landings:
        rows = bind.execute(
            sa.text(
                "SELECT p.id, p.category FROM landing_products lp "
                "JOIN products p ON p.id = lp.product_id "
                "WHERE lp.landing_id = :lid ORDER BY lp.sort_order"
            ),
            {"lid": lid},
        ).fetchall()
        content = default_content(groups_from_category_rows(rows))
        bind.execute(
            sa.text("UPDATE landings SET content = CAST(:c AS jsonb) WHERE id = :lid"),
            {"c": json.dumps(content), "lid": lid},
        )


def downgrade() -> None:
    op.drop_column("landings", "content")
