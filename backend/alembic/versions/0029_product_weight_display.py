"""Product weight_display: free-text weight range (e.g. «۱۲-۱۵ گرم») for
sets/pieces whose weight is a range the single numeric can't express.

Revision ID: 0029
Revises: 0028
Create Date: 2026-08-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("weight_display", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "weight_display")
