"""ORM model linking a manga to its rating from an external source."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base

if TYPE_CHECKING:
    from manga_recommender.db.models.manga import Manga


class MangaExternalRating(Base):
    """ORM model for a manga's raw rating data from one external source.

    Unique per (source, external_id). A manga can hold more than one rating
    from the same source when merged source entries each keep their own score.
    """

    __tablename__ = "manga_external_ratings"

    # Indexed: Postgres does not index a foreign key on its own, and every
    # cascade delete and rating lookup filters on this column.
    manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column()
    raw_scale_max: Mapped[float | None] = mapped_column()
    votes_count: Mapped[int | None] = mapped_column()
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_score: Mapped[float | None] = mapped_column()
    score_distribution: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    manga: Mapped["Manga"] = relationship(back_populates="external_ratings")

    __table_args__ = (UniqueConstraint("source_id", "external_id"),)
