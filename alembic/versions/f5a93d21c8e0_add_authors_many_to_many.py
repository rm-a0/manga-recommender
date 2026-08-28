"""add authors many to many

Revision ID: f5a93d21c8e0
Revises: 8e2c60fa71b4
Create Date: 2026-08-28 21:42:00.000000

Replaces the comma-joined `manga.author` string with an authors table and a
link table, mirroring genres. `normalized_name` is the identity key, so the
same person written two ways ("Inoue, Takehiko" and "Takehiko Inoue") stays
one row across sources.

Splitting the old column on a comma is only correct for rows the AniList
extractor wrote, which joined whole names. Kaggle names are themselves
"Last, First", so splitting one would invent two authors. The old column does
not record which extractor wrote it, so the backfill covers only manga that
hold an AniList rating. Kaggle-only manga keep no authors until an ingest
fills them in.
"""

import re
import unicodedata
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a93d21c8e0"
down_revision: str | Sequence[str] | None = "8e2c60fa71b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The extractors used to write this when a record had no named staff. It is
# not an author, so it must not become a row.
_PLACEHOLDER = "Unknown"


def _normalize(name: str) -> str:
    """Frozen copy of `normalize_author_name` at this revision."""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    parts = [part for part in re.split(r"[^a-z0-9]+", stripped.lower()) if part]
    return " ".join(sorted(parts))


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "authors",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("normalized_name", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index("ix_authors_normalized_name", "authors", ["normalized_name"])
    op.create_table(
        "manga_authors",
        sa.Column("manga_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("manga_id", "author_id"),
    )

    bind = op.get_bind()
    # Only manga carrying an AniList rating have an AniList-written author
    # string. See the module docstring.
    rows = bind.execute(
        sa.text(
            """
            SELECT DISTINCT m.id, m.author
            FROM manga m
            JOIN manga_external_ratings r ON r.manga_id = m.id
            JOIN sources s ON s.id = r.source_id AND s.name = 'anilist'
            WHERE m.author IS NOT NULL
            """
        )
    ).all()

    author_ids: dict[str, uuid.UUID] = {}
    author_rows: list[dict] = []
    link_rows: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for manga_id, author in rows:
        for part in author.split(","):
            display = part.strip()
            key = _normalize(display)
            if not key or display == _PLACEHOLDER:
                continue
            if key not in author_ids:
                author_ids[key] = uuid.uuid4()
                author_rows.append(
                    {"id": author_ids[key], "name": display, "normalized_name": key}
                )
            link_rows.add((manga_id, author_ids[key]))

    if author_rows:
        bind.execute(
            sa.text(
                "INSERT INTO authors (id, name, normalized_name) "
                "VALUES (:id, :name, :normalized_name)"
            ),
            author_rows,
        )
    if link_rows:
        bind.execute(
            sa.text("INSERT INTO manga_authors (manga_id, author_id) VALUES (:m, :a)"),
            [{"m": m, "a": a} for m, a in link_rows],
        )

    op.drop_column("manga", "author")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("manga", sa.Column("author", sa.String(), nullable=True))
    op.execute(
        f"""
        UPDATE manga m
        SET author = COALESCE(joined.names, '{_PLACEHOLDER}')
        FROM (
            SELECT ma.manga_id, string_agg(a.name, ', ' ORDER BY a.name) AS names
            FROM manga_authors ma
            JOIN authors a ON a.id = ma.author_id
            GROUP BY ma.manga_id
        ) joined
        WHERE joined.manga_id = m.id
        """
    )
    op.execute(f"UPDATE manga SET author = '{_PLACEHOLDER}' WHERE author IS NULL")
    op.alter_column("manga", "author", nullable=False)

    op.drop_table("manga_authors")
    op.drop_index("ix_authors_normalized_name", table_name="authors")
    op.drop_table("authors")
