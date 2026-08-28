"""Author ORM model and its many-to-many link to manga."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base

if TYPE_CHECKING:
    from manga_recommender.db.models.manga import Manga

manga_authors = Table(
    "manga_authors",
    Base.metadata,
    Column("manga_id", ForeignKey("manga.id", ondelete="CASCADE"), primary_key=True),
    # The composite primary key covers manga_id only. A lookup by
    # author_id alone needs its own index.
    Column(
        "author_id",
        ForeignKey("authors.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Author(Base):
    """ORM model for a manga author.

    `name` is the spelling to show. `normalized_name` is the identity key, so
    one person written several ways stays one row.
    """

    __tablename__ = "authors"

    name: Mapped[str] = mapped_column()
    normalized_name: Mapped[str] = mapped_column(unique=True, index=True)
    manga: Mapped[list["Manga"]] = relationship(
        secondary=manga_authors, back_populates="authors"
    )
