"""Source ORM model for external data providers."""

from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base


class Source(Base):
    """ORM model for an external data source (e.g. AniList) and its scoring weight."""

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(unique=True)
    weight: Mapped[float] = mapped_column(default=1.0)
