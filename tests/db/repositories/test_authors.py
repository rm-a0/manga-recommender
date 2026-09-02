import uuid

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.authors import (
    bulk_get_or_create_authors,
    count_authors,
    create_author,
    get_all_authors,
    get_author_by_id,
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


# --- get_author_by_id ---


def test_get_author_by_id_returns_matching_author(db_session: Session) -> None:
    created = create_author(db_session, name="Kentaro Miura")

    found = get_author_by_id(db_session, created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Kentaro Miura"


def test_get_author_by_id_returns_none_when_missing(db_session: Session) -> None:
    assert get_author_by_id(db_session, uuid.uuid4()) is None


# --- get_all_authors ---


def test_get_all_authors_orders_by_name(db_session: Session) -> None:
    for name in ("Naoki Urasawa", "Akira Toriyama", "Junji Ito"):
        create_author(db_session, name=name)

    found = get_all_authors(db_session, limit=10, offset=0)

    assert [a.name for a in found] == [
        "Akira Toriyama",
        "Junji Ito",
        "Naoki Urasawa",
    ]


def test_get_all_authors_pages_without_repeating_or_skipping(
    db_session: Session,
) -> None:
    """Offset paging is only stable when the query orders deterministically."""
    created = {
        create_author(db_session, name=name).id
        for name in ("Akira Toriyama", "Junji Ito", "Naoki Urasawa", "Q Hayashida")
    }

    first = get_all_authors(db_session, limit=2, offset=0)
    second = get_all_authors(db_session, limit=2, offset=2)

    assert len(first) == 2
    assert len(second) == 2
    assert {a.id for a in first}.isdisjoint({a.id for a in second})
    assert {a.id for a in first} | {a.id for a in second} == created


def test_get_all_authors_returns_empty_past_the_last_page(db_session: Session) -> None:
    create_author(db_session, name="Kentaro Miura")

    assert get_all_authors(db_session, limit=10, offset=10) == []


# --- count_authors ---


def test_count_authors_counts_every_row_not_only_a_page(db_session: Session) -> None:
    assert count_authors(db_session) == 0
    for name in ("Akira Toriyama", "Junji Ito", "Naoki Urasawa"):
        create_author(db_session, name=name)

    assert count_authors(db_session) == 3


def test_count_authors_counts_merged_spellings_once(db_session: Session) -> None:
    """One person written two ways is one row, so one count."""
    get_or_create_author(db_session, name="Inoue, Takehiko")
    get_or_create_author(db_session, name="Takehiko Inoue")

    assert count_authors(db_session) == 1


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
