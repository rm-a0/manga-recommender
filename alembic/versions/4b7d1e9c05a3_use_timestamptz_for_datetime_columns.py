"""use timestamptz for datetime columns

Revision ID: 4b7d1e9c05a3
Revises: 591b389bfedd
Create Date: 2026-08-28 21:40:00.000000

The extractors always write aware UTC datetimes, so the stored values are
already UTC wall-clock. `USING <col> AT TIME ZONE 'UTC'` states that instead of
letting Postgres read them in the session's TimeZone.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b7d1e9c05a3"
down_revision: str | Sequence[str] | None = "591b389bfedd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("manga_external_ratings", "fetched_at", False),
    ("manga", "published_date", True),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table, column, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
