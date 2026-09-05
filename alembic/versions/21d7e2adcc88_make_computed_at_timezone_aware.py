"""make computed_at timezone aware

Revision ID: 21d7e2adcc88
Revises: f986558dad8c
Create Date: 2026-09-05 21:26:02.141552

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21d7e2adcc88"
down_revision: str | Sequence[str] | None = "f986558dad8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make computed_at timezone aware."""
    op.alter_column(
        "manga_metrics",
        "computed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert computed_at to a naive timestamp."""
    op.alter_column(
        "manga_metrics",
        "computed_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
