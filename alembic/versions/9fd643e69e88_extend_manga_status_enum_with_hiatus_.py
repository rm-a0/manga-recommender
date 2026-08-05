"""extend manga_status enum with hiatus and not_released_yet

Revision ID: 9fd643e69e88
Revises: c2ee0044922b
Create Date: 2026-08-05 22:18:31.968806

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9fd643e69e88"
down_revision: str | Sequence[str] | None = "c2ee0044922b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE manga_status RENAME VALUE 'completed' TO 'finished'")
    op.execute("ALTER TYPE manga_status ADD VALUE 'hiatus'")
    op.execute("ALTER TYPE manga_status ADD VALUE 'not_released_yet'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE manga_status RENAME VALUE 'finished' TO 'completed'")
    # Postgres has no DROP VALUE for enums; removing 'hiatus'/'not_released_yet'
    # on downgrade would require rebuilding the type entirely. Left as a no-op
    # since no data depends on it yet.
