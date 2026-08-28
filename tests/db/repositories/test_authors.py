import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.authors import (
    bulk_get_or_create_authors,
    create_author,
    get_author_by_name,
    get_or_create_author,
    normalize_author_name,
)


def test_create_author_persists_given_name(db_session: Session) -> None:
    author = create_author(db_session, name="action")

    assert author.id is not None
    assert author.name == "action"


def test_get_author_by_name_returns_matching_author(db_session: Session) -> None:
    created = create_author(db_session, name="drama")

    found = get_author_by_name(db_session, "drama")

    assert found is not None
    assert found.id == created.id


def test_get_author_by_name_returns_none_when_missing(db_session: Session) -> None:
    assert get_author_by_name(db_session, "no-such-author") is None


def test_get_or_create_author_returns_existing_author(db_session: Session) -> None:
    created = create_author(db_session, name="comedy")

    found = get_or_create_author(db_session, name="comedy")

    assert found.id == created.id


def test_get_or_create_author_creates_when_missing(db_session: Session) -> None:
    author = get_or_create_author(db_session, name="horror")

    assert author.id is not None
    assert get_author_by_name(db_session, "horror") is not None


# --- normalize_author_name ---


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Inoue, Takehiko", "Takehiko Inoue"),
        ("Urasawa, Naoki", "Naoki Urasawa"),
        ("mako", "Mako"),
        ("Aya, Ishida", "Ishida, Aya"),
        ("Yui", "ｙui"),
    ],
)
def test_normalize_author_name_folds_spellings_of_one_person(
    first: str, second: str
) -> None:
    assert normalize_author_name(first) == normalize_author_name(second)


def test_normalize_author_name_keeps_different_people_apart() -> None:
    assert normalize_author_name("Naoki Urasawa") != normalize_author_name(
        "Takehiko Inoue"
    )


def test_normalize_author_name_is_empty_for_a_name_with_no_word_characters() -> None:
    assert normalize_author_name("???") == ""


# --- bulk_get_or_create_authors ---


def test_bulk_get_or_create_authors_merges_spellings_into_one_row(
    db_session: Session,
) -> None:
    result = bulk_get_or_create_authors(
        db_session, ["Inoue, Takehiko", "Takehiko Inoue"]
    )

    assert result["Inoue, Takehiko"] == result["Takehiko Inoue"]
    assert len(set(result.values())) == 1


def test_bulk_get_or_create_authors_merges_across_separate_calls(
    db_session: Session,
) -> None:
    """The Kaggle spelling must land on the row the AniList spelling created."""
    first = bulk_get_or_create_authors(db_session, ["Naoki Urasawa"])

    second = bulk_get_or_create_authors(db_session, ["Urasawa, Naoki"])

    assert second["Urasawa, Naoki"] == first["Naoki Urasawa"]


def test_bulk_get_or_create_authors_prefers_the_comma_free_spelling(
    db_session: Session,
) -> None:
    bulk_get_or_create_authors(db_session, ["Tezuka, Osamu"])

    bulk_get_or_create_authors(db_session, ["Osamu Tezuka"])

    author = get_author_by_name(db_session, "Tezuka, Osamu")
    assert author is not None
    assert author.name == "Osamu Tezuka"


def test_bulk_get_or_create_authors_keeps_the_stored_spelling_when_no_better(
    db_session: Session,
) -> None:
    bulk_get_or_create_authors(db_session, ["Q Hayashida"])

    bulk_get_or_create_authors(db_session, ["Hayashida, Q"])

    author = get_author_by_name(db_session, "Q Hayashida")
    assert author is not None
    assert author.name == "Q Hayashida"


def test_bulk_get_or_create_authors_skips_a_name_that_normalizes_to_nothing(
    db_session: Session,
) -> None:
    result = bulk_get_or_create_authors(db_session, ["???", "Naoki Urasawa"])

    assert "???" not in result
    assert "Naoki Urasawa" in result


def test_get_author_by_name_finds_any_spelling(db_session: Session) -> None:
    created = create_author(db_session, name="Takehiko Inoue")

    assert get_author_by_name(db_session, "Inoue, Takehiko").id == created.id
