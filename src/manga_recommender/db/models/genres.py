from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base

if TYPE_CHECKING:
    from manga_recommender.db.models.manga import Manga

manga_genres = Table(
    "manga_genres",
    Base.metadata,
    Column("manga_id", ForeignKey("manga.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    name: Mapped[str] = mapped_column(unique=True)
    manga: Mapped[list["Manga"]] = relationship(
        secondary=manga_genres, back_populates="genres"
    )
