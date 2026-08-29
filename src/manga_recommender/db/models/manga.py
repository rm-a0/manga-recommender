"""Manga ORM model and status enum."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base, enum_values
from manga_recommender.db.models.authors import Author, manga_authors
from manga_recommender.db.models.tags import Tag, manga_tags

if TYPE_CHECKING:
    from manga_recommender.db.models.manga_external_ratings import MangaExternalRating


class MangaStatus(StrEnum):
    """Publication status of a manga."""

    ONGOING = "ongoing"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    NOT_RELEASED_YET = "not_released_yet"
    HIATUS = "hiatus"


class Manga(Base):
    """ORM model for a manga entry and its metadata."""

    __tablename__ = "manga"

    mal_id: Mapped[int | None] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column()
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column()
    status: Mapped[MangaStatus | None] = mapped_column(
        Enum(MangaStatus, name="manga_status", values_callable=enum_values)
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=manga_tags, back_populates="manga"
    )
    authors: Mapped[list["Author"]] = relationship(
        secondary=manga_authors, back_populates="manga"
    )
    # passive_deletes lets the database's ON DELETE CASCADE remove the child
    # rows. Without it, SQLAlchemy loads and deletes each one separately.
    external_ratings: Mapped[list["MangaExternalRating"]] = relationship(
        back_populates="manga",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
