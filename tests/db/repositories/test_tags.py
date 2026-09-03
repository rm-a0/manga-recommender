import uuid

import pytest
from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from manga_recommender.db.models.tags import manga_tags
from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    bulk_add_tags_to_manga,
    create_manga,
)
from manga_recommender.db.repositories.tags import (
    TagUpsertValues,
    bulk_get_or_create_tags,
    create_tag,
    get_all_tags,
    get_or_create_tag,
    get_tag_by_id,
    get_tag_by_name,
    normalize_tag_name,
)


def _link(db: Session, manga_id: uuid.UUID, tag_id: uuid.UUID) -> Row:
    """Return the manga_tags row for one pairing."""
    db.expire_all()
    return db.execute(
        select(manga_tags).where(
            manga_tags.c.manga_id == manga_id,
            manga_tags.c.tag_id == tag_id,
        )
    ).one()


def test_create_tag_persists_given_name(db_session: Session) -> None:
    tag = create_tag(db_session, name="Isekai", category="Theme")

    assert tag.id is not None
    assert tag.name == "Isekai"
    assert tag.category == "Theme"


def test_get_tag_by_name_returns_matching_tag(db_session: Session) -> None:
    created = create_tag(db_session, name="Mecha", category=None)

    found = get_tag_by_name(db_session, "Mecha")

    assert found is not None
    assert found.id == created.id


def test_get_tag_by_name_returns_none_when_missing(db_session: Session) -> None:
    assert get_tag_by_name(db_session, "no-such-tag") is None


def test_get_tag_by_name_finds_any_spelling(db_session: Session) -> None:
    created = create_tag(db_session, name="Sci-Fi", category=None)

    found = get_tag_by_name(db_session, "sci fi")

    assert found is not None
    assert found.id == created.id


def test_get_or_create_tag_returns_existing_tag(db_session: Session) -> None:
    created = create_tag(db_session, name="Comedy", category=None)

    found = get_or_create_tag(db_session, name="Comedy", category=None)

    assert found.id == created.id


def test_get_or_create_tag_creates_when_missing(db_session: Session) -> None:
    tag = get_or_create_tag(db_session, name="Horror", category=None)

    assert tag.id is not None
    assert get_tag_by_name(db_session, "Horror") is not None


# --- normalize_tag_name ---


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Sci-Fi", "Sci Fi"),
        ("Slice of Life", "slice of life"),
        ("Time  Travel", "time travel"),
        ("Mahou Shoujo", "mahou-shoujo"),
        ("Shōjo", "Shojo"),
    ],
)
def test_normalize_tag_name_folds_spellings_of_one_tag(first: str, second: str) -> None:
    assert normalize_tag_name(first) == normalize_tag_name(second)


def test_normalize_tag_name_keeps_word_order() -> None:
    """Word order carries meaning, so the key must not sort its parts."""
    assert normalize_tag_name("Time Travel") != normalize_tag_name("Travel Time")


def test_normalize_tag_name_keeps_different_tags_apart() -> None:
    assert normalize_tag_name("Shounen Ai") != normalize_tag_name("Shoujo Ai")


def test_normalize_tag_name_is_empty_for_a_name_with_no_word_characters() -> None:
    assert normalize_tag_name("???") == ""


# --- bulk_get_or_create_tags ---


def test_bulk_get_or_create_tags_merges_spellings_into_one_row(
    db_session: Session,
) -> None:
    result = bulk_get_or_create_tags(
        db_session,
        [
            TagUpsertValues(name="Sci-Fi", category=None),
            TagUpsertValues(name="sci fi", category=None),
        ],
    )

    assert result["Sci-Fi"] == result["sci fi"]
    assert len(set(result.values())) == 1


def test_bulk_get_or_create_tags_returns_every_multi_word_name(
    db_session: Session,
) -> None:
    """The result lookup must use the tag key, which keeps word order."""
    names = ["Slice of Life", "Time Travel", "Sci-Fi", "Action"]

    result = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name=n, category=None) for n in names]
    )

    assert set(result) == set(names)


def test_bulk_get_or_create_tags_keeps_the_first_spelling(db_session: Session) -> None:
    bulk_get_or_create_tags(db_session, [TagUpsertValues(name="Sci-Fi", category=None)])

    bulk_get_or_create_tags(db_session, [TagUpsertValues(name="sci fi", category=None)])

    tag = get_tag_by_name(db_session, "Sci-Fi")
    assert tag is not None
    assert tag.name == "Sci-Fi"


def test_bulk_get_or_create_tags_merges_across_separate_calls(
    db_session: Session,
) -> None:
    """The Kaggle spelling must land on the row the AniList spelling created."""
    first = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Mahou Shoujo", category="Theme")]
    )

    second = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="mahou-shoujo", category=None)]
    )

    assert second["mahou-shoujo"] == first["Mahou Shoujo"]


def test_bulk_get_or_create_tags_keeps_a_category_a_later_source_omits(
    db_session: Session,
) -> None:
    """Kaggle supplies no category, so it must not clear the AniList one."""
    bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Isekai", category="Theme")]
    )

    bulk_get_or_create_tags(db_session, [TagUpsertValues(name="Isekai", category=None)])

    tag = get_tag_by_name(db_session, "Isekai")
    assert tag is not None
    assert tag.category == "Theme"


def test_bulk_get_or_create_tags_fills_a_category_left_empty(
    db_session: Session,
) -> None:
    bulk_get_or_create_tags(db_session, [TagUpsertValues(name="Isekai", category=None)])

    bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Isekai", category="Theme")]
    )

    tag = get_tag_by_name(db_session, "Isekai")
    assert tag is not None
    assert tag.category == "Theme"


def test_bulk_get_or_create_tags_skips_a_name_that_normalizes_to_nothing(
    db_session: Session,
) -> None:
    result = bulk_get_or_create_tags(
        db_session,
        [
            TagUpsertValues(name="???", category=None),
            TagUpsertValues(name="Action", category=None),
        ],
    )

    assert "???" not in result
    assert "Action" in result


def test_bulk_get_or_create_tags_tolerates_duplicate_names(db_session: Session) -> None:
    """Duplicate names in one call must collapse, not raise CardinalityViolation."""
    result = bulk_get_or_create_tags(
        db_session,
        [
            TagUpsertValues(name="Seinen", category=None),
            TagUpsertValues(name="Seinen", category=None),
            TagUpsertValues(name="Josei", category=None),
        ],
    )

    assert set(result) == {"Seinen", "Josei"}


# --- bulk_add_tags_to_manga ---


def test_bulk_add_tags_to_manga_writes_rank_and_spoiler(db_session: Session) -> None:
    manga = create_manga(db_session, title="Steins;Gate")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Time Travel", category="Theme")]
    )

    bulk_add_tags_to_manga(
        db_session,
        [
            TagLinkValues(
                manga_id=manga.id,
                tag_id=tag_ids["Time Travel"],
                rank=87,
                is_spoiler=True,
            )
        ],
    )

    row = _link(db_session, manga.id, tag_ids["Time Travel"])
    assert row.rank == 87
    assert row.is_spoiler is True


def test_bulk_add_tags_to_manga_keeps_a_rank_a_later_source_omits(
    db_session: Session,
) -> None:
    """Kaggle supplies no rank, so it must not clear the AniList one."""
    manga = create_manga(db_session, title="Berserk")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Dark Fantasy", category=None)]
    )
    link = TagLinkValues(
        manga_id=manga.id, tag_id=tag_ids["Dark Fantasy"], rank=91, is_spoiler=False
    )
    bulk_add_tags_to_manga(db_session, [link])

    bulk_add_tags_to_manga(db_session, [{**link, "rank": None}])

    assert _link(db_session, manga.id, tag_ids["Dark Fantasy"]).rank == 91


def test_bulk_add_tags_to_manga_fills_a_rank_left_empty(db_session: Session) -> None:
    manga = create_manga(db_session, title="Vinland Saga")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Historical", category=None)]
    )
    link = TagLinkValues(
        manga_id=manga.id, tag_id=tag_ids["Historical"], rank=None, is_spoiler=False
    )
    bulk_add_tags_to_manga(db_session, [link])

    bulk_add_tags_to_manga(db_session, [{**link, "rank": 64}])

    assert _link(db_session, manga.id, tag_ids["Historical"]).rank == 64


def test_bulk_add_tags_to_manga_never_clears_a_spoiler_flag(
    db_session: Session,
) -> None:
    """A source that flags no spoiler must not unhide a flagged tag."""
    manga = create_manga(db_session, title="Oyasumi Punpun")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Tragedy", category=None)]
    )
    link = TagLinkValues(
        manga_id=manga.id, tag_id=tag_ids["Tragedy"], rank=None, is_spoiler=True
    )
    bulk_add_tags_to_manga(db_session, [link])

    bulk_add_tags_to_manga(db_session, [{**link, "is_spoiler": False}])

    assert _link(db_session, manga.id, tag_ids["Tragedy"]).is_spoiler is True


def test_bulk_add_tags_to_manga_raises_a_spoiler_flag(db_session: Session) -> None:
    manga = create_manga(db_session, title="Monster")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Twist", category=None)]
    )
    link = TagLinkValues(
        manga_id=manga.id, tag_id=tag_ids["Twist"], rank=None, is_spoiler=False
    )
    bulk_add_tags_to_manga(db_session, [link])

    bulk_add_tags_to_manga(db_session, [{**link, "is_spoiler": True}])

    assert _link(db_session, manga.id, tag_ids["Twist"]).is_spoiler is True


def test_bulk_add_tags_to_manga_tolerates_duplicate_links(db_session: Session) -> None:
    """One tag repeated in a record must collapse, not raise CardinalityViolation."""
    manga = create_manga(db_session, title="Dorohedoro")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="Gore", category=None)]
    )
    link = TagLinkValues(
        manga_id=manga.id, tag_id=tag_ids["Gore"], rank=55, is_spoiler=False
    )

    bulk_add_tags_to_manga(db_session, [link, link])

    assert _link(db_session, manga.id, tag_ids["Gore"]).rank == 55


def test_bulk_add_tags_to_manga_does_nothing_with_no_links(db_session: Session) -> None:
    bulk_add_tags_to_manga(db_session, [])


# --- get_tag_by_id ---


def test_get_tag_by_id_returns_matching_tag(db_session: Session) -> None:
    created = create_tag(db_session, name="Mecha", category="Theme")

    found = get_tag_by_id(db_session, created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Mecha"


def test_get_tag_by_id_returns_none_when_missing(db_session: Session) -> None:
    assert get_tag_by_id(db_session, uuid.uuid4()) is None


# --- get_all_tags ---


def test_get_all_tags_orders_by_name(db_session: Session) -> None:
    for name in ("Seinen", "Action", "Mecha"):
        create_tag(db_session, name=name, category=None)

    found = get_all_tags(db_session, limit=10, offset=0)

    assert [t.name for t in found] == ["Action", "Mecha", "Seinen"]


def test_get_all_tags_pages_without_repeating_or_skipping(
    db_session: Session,
) -> None:
    created = {
        create_tag(db_session, name=name, category=None).id
        for name in ("Action", "Mecha", "Seinen", "Tragedy")
    }

    first = get_all_tags(db_session, limit=2, offset=0)
    second = get_all_tags(db_session, limit=2, offset=2)

    assert {t.id for t in first}.isdisjoint({t.id for t in second})
    assert {t.id for t in first} | {t.id for t in second} == created


def test_get_all_tags_returns_empty_past_the_last_page(db_session: Session) -> None:
    create_tag(db_session, name="Action", category=None)

    assert get_all_tags(db_session, limit=10, offset=10) == []


def test_get_all_tags_returns_empty_with_no_tags(db_session: Session) -> None:
    assert get_all_tags(db_session, limit=10, offset=0) == []
