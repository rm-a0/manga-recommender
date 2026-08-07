from datetime import datetime

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import (
    create_manga,
    delete_manga,
    get_manga_by_mal_id,
    get_manga_by_source_external_id,
    update_manga,
)


def test_create_manga_persists_given_fields(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        mal_id=1,
        title="One Piece",
        author="Eiichiro Oda",
        status=MangaStatus.ONGOING,
    )

    assert manga.id is not None
    assert manga.mal_id == 1
    assert manga.title == "One Piece"
    assert manga.author == "Eiichiro Oda"
    assert manga.status == MangaStatus.ONGOING


def test_create_manga_defaults_optional_fields_to_none(db_session: Session) -> None:
    manga = create_manga(db_session, title="Berserk", author="Kentaro Miura")

    assert manga.mal_id is None
    assert manga.published_date is None
    assert manga.status is None


def test_get_manga_by_mal_id_returns_matching_manga(db_session: Session) -> None:
    created = create_manga(
        db_session, mal_id=2, title="Vagabond", author="Takehiko Inoue"
    )

    found = get_manga_by_mal_id(db_session, 2)

    assert found is not None
    assert found.id == created.id


def test_get_manga_by_mal_id_returns_none_when_missing(db_session: Session) -> None:
    assert get_manga_by_mal_id(db_session, 999_999) is None


def test_update_manga_overwrites_only_given_fields(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        title="Chainsaw Man",
        author="Tatsuki Fujimoto",
        status=MangaStatus.ONGOING,
    )

    updated = update_manga(db_session, manga, status=MangaStatus.FINISHED)

    assert updated.status == MangaStatus.FINISHED
    assert updated.title == "Chainsaw Man"
    assert updated.author == "Tatsuki Fujimoto"


def test_update_manga_with_no_args_changes_nothing(db_session: Session) -> None:
    manga = create_manga(db_session, title="Dandadan", author="Yukinobu Tatsu")

    updated = update_manga(db_session, manga)

    assert updated.title == "Dandadan"
    assert updated.author == "Yukinobu Tatsu"


def test_delete_manga_removes_the_row(db_session: Session) -> None:
    manga = create_manga(
        db_session, mal_id=3, title="Oyasumi Punpun", author="Inio Asano"
    )

    delete_manga(db_session, manga)

    assert get_manga_by_mal_id(db_session, 3) is None


def test_get_manga_by_source_external_id_returns_matching_manga(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Solo Leveling", author="Chugong")
    db_session.add(
        MangaExternalRating(
            manga_id=manga.id,
            source_id=test_source.id,
            external_id="ext-1",
            fetched_at=datetime.now(),
        )
    )
    db_session.flush()

    found = get_manga_by_source_external_id(db_session, test_source.id, "ext-1")

    assert found is not None
    assert found.id == manga.id


def test_get_manga_by_source_external_id_returns_none_on_miss(
    db_session: Session, test_source: Source
) -> None:
    assert (
        get_manga_by_source_external_id(db_session, test_source.id, "no-such-id")
        is None
    )


def test_get_manga_by_source_external_id_does_not_cross_match(
    db_session: Session, test_source: Source
) -> None:
    manga_a = create_manga(db_session, title="Manga A", author="Author A")
    manga_b = create_manga(db_session, title="Manga B", author="Author B")
    db_session.add_all(
        [
            MangaExternalRating(
                manga_id=manga_a.id,
                source_id=test_source.id,
                external_id="ext-a",
                fetched_at=datetime.now(),
            ),
            MangaExternalRating(
                manga_id=manga_b.id,
                source_id=test_source.id,
                external_id="ext-b",
                fetched_at=datetime.now(),
            ),
        ]
    )
    db_session.flush()

    result_a = get_manga_by_source_external_id(db_session, test_source.id, "ext-a")
    result_b = get_manga_by_source_external_id(db_session, test_source.id, "ext-b")

    assert result_a is not None and result_a.id == manga_a.id
    assert result_b is not None and result_b.id == manga_b.id
