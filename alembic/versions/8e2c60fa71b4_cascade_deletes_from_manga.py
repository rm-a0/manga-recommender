"""cascade deletes from manga

Revision ID: 8e2c60fa71b4
Revises: 4b7d1e9c05a3
Create Date: 2026-08-28 21:41:00.000000

Alembic's autogenerate does not detect a changed ON DELETE, so these are
written by hand.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e2c60fa71b4"
down_revision: str | Sequence[str] | None = "4b7d1e9c05a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (constraint, table, column, referred table)
_FOREIGN_KEYS = (
    (
        "manga_external_ratings_manga_id_fkey",
        "manga_external_ratings",
        "manga_id",
        "manga",
    ),
    ("manga_genres_manga_id_fkey", "manga_genres", "manga_id", "manga"),
    ("manga_genres_genre_id_fkey", "manga_genres", "genre_id", "genres"),
)


def _recreate(ondelete: str | None) -> None:
    """Drop and recreate every listed foreign key with the given ON DELETE."""
    for name, table, column, referred in _FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name, table, referred, [column], ["id"], ondelete=ondelete
        )


def upgrade() -> None:
    """Upgrade schema."""
    _recreate("CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    _recreate(None)
