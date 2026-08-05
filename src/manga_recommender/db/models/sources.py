from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(unique=True)
    weight: Mapped[float] = mapped_column(default=1.0)
