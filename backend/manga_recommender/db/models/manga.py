"""Manga ORM model, with its status and type enums."""

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base, enum_values
from manga_recommender.db.models.authors import Author, manga_authors
from manga_recommender.db.models.tags import Tag, manga_tags

if TYPE_CHECKING:
    from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
    from manga_recommender.db.models.manga_metrics import MangaMetric


class MangaStatus(StrEnum):
    """Publication status of a manga."""

    ONGOING = "ongoing"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    NOT_RELEASED_YET = "not_released_yet"
    HIATUS = "hiatus"


class MangaType(StrEnum):
    """Medium of a manga entry.

    Both sources carry it, but they do not agree on shape: Kaggle MAL sends one
    value per member, and AniList sends a format plus a country of origin.
    """

    MANGA = "manga"
    LIGHT_NOVEL = "light_novel"
    MANHWA = "manhwa"
    ONE_SHOT = "one_shot"
    DOUJINSHI = "doujinshi"
    MANHUA = "manhua"


class Manga(Base):
    """ORM model for a manga entry and its metadata."""

    __tablename__ = "manga"

    mal_id: Mapped[int | None] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column()
    type: Mapped[MangaType | None] = mapped_column(
        Enum(MangaType, name="manga_type", values_callable=enum_values)
    )
    title_english: Mapped[str | None] = mapped_column()
    published_date: Mapped[date | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()
    image_url: Mapped[str | None] = mapped_column()
    status: Mapped[MangaStatus | None] = mapped_column(
        Enum(MangaStatus, name="manga_status", values_callable=enum_values)
    )
    tags: Mapped[list[Tag]] = relationship(secondary=manga_tags, back_populates="manga")
    authors: Mapped[list[Author]] = relationship(
        secondary=manga_authors, back_populates="manga"
    )
    external_ratings: Mapped[list[MangaExternalRating]] = relationship(
        back_populates="manga",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    metric: Mapped[MangaMetric | None] = relationship(
        back_populates="manga",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
