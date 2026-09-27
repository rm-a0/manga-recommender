"""ORM model for a similarity score between two manga."""

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base, enum_values


class SimilarityMethod(StrEnum):
    """Kind of signal that produced a similarity score.

    `collab` comes from reading lists. `community_recs` comes from reader votes.
    """

    COMMUNITY_RECS = "community_recs"
    COLLAB = "collab"


class MangaSimilarity(Base):
    """ORM model for one directed similarity edge from one manga to another.

    A higher score means more similar. The scale depends on `method`.
    """

    __tablename__ = "manga_similarities"
    __table_args__ = (PrimaryKeyConstraint("manga_id", "method", "similar_manga_id"),)

    # Remove the UUID `id` from `Base`. The composite primary key identifies a row
    # and uses less space. mypy rejects the override because `Base` types `id` as UUID.
    id = None  # type: ignore[assignment]
    manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE")
    )
    method: Mapped[SimilarityMethod] = mapped_column(
        Enum(SimilarityMethod, name="similarity_method", values_callable=enum_values)
    )
    similar_manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column()
