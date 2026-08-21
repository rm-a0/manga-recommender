from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.ingestion.loader import _sync_genres_for_manga


def test_sync_genres_for_manga_attaches_genres(db_session: Session) -> None:
    manga = create_manga(db_session, title="One Piece", author="Eiichiro Oda")

    _sync_genres_for_manga(db_session, manga, ["Action", "Adventure"])

    assert {genre.name for genre in manga.genres} == {"action", "adventure"}


def test_sync_genres_for_manga_normalizes_names(db_session: Session) -> None:
    manga = create_manga(db_session, title="Berserk", author="Kentaro Miura")

    _sync_genres_for_manga(db_session, manga, [" Dark Fantasy ", "DARK FANTASY"])

    assert [genre.name for genre in manga.genres] == ["dark fantasy"]


def test_sync_genres_for_manga_does_not_duplicate_existing_genres(
    db_session: Session,
) -> None:
    manga = create_manga(db_session, title="Vagabond", author="Takehiko Inoue")
    _sync_genres_for_manga(db_session, manga, ["Action"])

    _sync_genres_for_manga(db_session, manga, ["Action", "Drama"])

    assert {genre.name for genre in manga.genres} == {"action", "drama"}
