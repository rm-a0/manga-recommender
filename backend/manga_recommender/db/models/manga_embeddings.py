"""ORM model for the content vector derived from a manga's text."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base


class MangaEmbedding(Base):
    """ORM model for the content vector computed for one manga.

    The `index` stage rebuilds every row from the embeddings artifact. A manga
    outside the export gate gets no row at all, not a row of NULLs.
    """

    __tablename__ = "manga_embeddings"
    __table_args__ = (
        Index(
            "ix_manga_embeddings_content_vector",
            "content_vector",
            postgresql_using="hnsw",
            postgresql_ops={"content_vector": "halfvec_ip_ops"},
        ),
    )

    manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), unique=True
    )
    content_vector: Mapped[list[float]] = mapped_column(HALFVEC(384))
    model_name: Mapped[str] = mapped_column()
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cluster_id: Mapped[int | None] = mapped_column()
