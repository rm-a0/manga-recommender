"""Genre ORM model and its many-to-many link to manga."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base

if TYPE_CHECKING:
    from manga_recommender.db.models.manga import Manga

manga_genres = Table(
    "manga_genres",
    Base.metadata,
    Column("manga_id", ForeignKey("manga.id", ondelete="CASCADE"), primary_key=True),
    # The composite primary key covers manga_id only. A lookup by
    # genre_id alone needs its own index.
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Genre(Base):
    """ORM model for a manga genre."""

    __tablename__ = "genres"

    name: Mapped[str] = mapped_column(unique=True)
    manga: Mapped[list["Manga"]] = relationship(
        secondary=manga_genres, back_populates="genres"
    )
