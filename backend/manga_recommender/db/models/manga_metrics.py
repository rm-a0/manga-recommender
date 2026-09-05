"""ORM model for the rating metrics derived from a manga's external ratings."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base


class MangaMetric(Base):
    """ORM model for the rating metrics computed for one manga.

    The `fill` stage rebuilds every row from `manga_external_ratings`. A manga
    with no usable source rating gets no row at all, not a row of NULLs.
    """

    __tablename__ = "manga_metrics"

    manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), unique=True
    )
    bayesian_score: Mapped[float] = mapped_column(index=True)
    mean_score: Mapped[float] = mapped_column()
    votes_count: Mapped[int] = mapped_column()
    source_count: Mapped[int] = mapped_column()
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
