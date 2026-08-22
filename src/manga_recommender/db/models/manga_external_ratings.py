"""ORM model linking a manga to its rating from an external source."""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base


class MangaExternalRating(Base):
    """ORM model for a manga's raw rating data from one external source.

    Unique per (manga, source) and per (source, external_id).
    """

    __tablename__ = "manga_external_ratings"

    manga_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("manga.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column()
    raw_scale_max: Mapped[float | None] = mapped_column()
    votes_count: Mapped[int | None] = mapped_column()
    fetched_at: Mapped[datetime] = mapped_column()
    raw_score: Mapped[float | None] = mapped_column()
    score_distribution: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    __table_args__ = (
        UniqueConstraint("manga_id", "source_id"),
        UniqueConstraint("source_id", "external_id"),
    )
