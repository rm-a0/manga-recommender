from sqlalchemy.orm import Session

from manga_recommender.db.repositories.sources import (
    create_source,
    delete_source,
    get_or_create_source,
    get_source_by_name,
    get_source_id_by_name,
)


def test_create_source_persists_given_fields(db_session: Session) -> None:
    source = create_source(db_session, name="anilist", weight=0.8)

    assert source.id is not None
    assert source.name == "anilist"
    assert source.weight == 0.8


def test_create_source_defaults_weight_to_one(db_session: Session) -> None:
    source = create_source(db_session, name="mangadex")

    assert source.weight == 1.0


def test_get_source_by_name_returns_matching_source(db_session: Session) -> None:
    created = create_source(db_session, name="mal")

    found = get_source_by_name(db_session, "mal")

    assert found is not None
    assert found.id == created.id


def test_get_source_by_name_returns_none_when_missing(db_session: Session) -> None:
    assert get_source_by_name(db_session, "no-such-source") is None


def test_get_or_create_source_returns_existing_source(db_session: Session) -> None:
    created = create_source(db_session, name="kitsu")

    found = get_or_create_source(db_session, name="kitsu")

    assert found.id == created.id


def test_get_or_create_source_creates_when_missing(db_session: Session) -> None:
    source = get_or_create_source(db_session, name="novelupdates", weight=0.5)

    assert source.id is not None
    assert source.weight == 0.5


def test_get_source_id_by_name_returns_matching_id(db_session: Session) -> None:
    created = create_source(db_session, name="anilist")

    assert get_source_id_by_name(db_session, "anilist") == created.id


def test_get_source_id_by_name_returns_none_when_missing(db_session: Session) -> None:
    assert get_source_id_by_name(db_session, "no-such-source") is None


def test_delete_source_removes_the_row(db_session: Session) -> None:
    source = create_source(db_session, name="temp-source")

    delete_source(db_session, source)

    assert get_source_by_name(db_session, "temp-source") is None
