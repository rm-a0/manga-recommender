from datetime import datetime
import uuid

from manga_recommender.db.base import Base
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class MangaEmbedding(Base):
    __tablename__ = "manga_embeddings"

    manga_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manga.id", ondelete="CASCADE"), unique=True
    )
    content_vector: Mapped[list[float]] = mapped_column(HALFVEC(384))
    model_name: Mapped[str] = mapped_column()
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cluster_id: Mapped[int | None] = mapped_column()
