from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db.models.genres import Genre, manga_genres


class MangaStatus(StrEnum):
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Manga(Base):
    __tablename__ = "manga"

    title: Mapped[str] = mapped_column()
    author: Mapped[str] = mapped_column()
    published_date: Mapped[datetime | None] = mapped_column()
    status: Mapped[MangaStatus | None] = mapped_column(
        Enum(MangaStatus, name="manga_status")
    )
    genres: Mapped[list["Genre"]] = relationship(
        secondary=manga_genres, back_populates="manga"
    )
