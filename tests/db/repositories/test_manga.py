import uuid
from datetime import datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.authors import get_or_create_author
from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    assign_authors_to_manga,
    bulk_add_tags_to_manga,
    count_manga,
    count_manga_by_author_id,
    count_manga_by_tag_id,
    create_manga,
    delete_manga,
    get_all_manga,
    get_manga_by_author_id,
    get_manga_by_id,
    get_manga_by_mal_id,
    get_manga_by_source_external_id,
    get_manga_by_tag_id,
    get_manga_tag_links,
    update_manga,
)
from manga_recommender.db.repositories.tags import get_or_create_tag


def test_create_manga_persists_given_fields(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        mal_id=1,
        title="One Piece",
        description="A boy sets out to become the Pirate King.",
        image_url="https://cdn.test/one-piece.jpg",
        status=MangaStatus.ONGOING,
    )

    assert manga.id is not None
    assert manga.mal_id == 1
    assert manga.title == "One Piece"
    assert manga.description == "A boy sets out to become the Pirate King."
    assert manga.image_url == "https://cdn.test/one-piece.jpg"
    assert manga.status == MangaStatus.ONGOING


def test_create_manga_defaults_optional_fields_to_none(db_session: Session) -> None:
    manga = create_manga(db_session, title="Berserk")

    assert manga.mal_id is None
    assert manga.published_date is None
    assert manga.description is None
    assert manga.image_url is None
    assert manga.status is None


def test_get_manga_by_mal_id_returns_matching_manga(db_session: Session) -> None:
    created = create_manga(db_session, mal_id=2, title="Vagabond")

    found = get_manga_by_mal_id(db_session, 2)

    assert found is not None
    assert found.id == created.id


def test_get_manga_by_mal_id_returns_none_when_missing(db_session: Session) -> None:
    assert get_manga_by_mal_id(db_session, 999_999) is None


def test_update_manga_overwrites_only_given_fields(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        title="Chainsaw Man",
        status=MangaStatus.ONGOING,
    )

    updated = update_manga(db_session, manga, status=MangaStatus.FINISHED)

    assert updated.status == MangaStatus.FINISHED
    assert updated.title == "Chainsaw Man"


def test_update_manga_updates_description(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        title="Chainsaw Man",
        description="Original description.",
    )

    updated = update_manga(db_session, manga, description="Updated description.")

    assert updated.description == "Updated description."
    assert updated.title == "Chainsaw Man"


def test_update_manga_updates_image_url(db_session: Session) -> None:
    manga = create_manga(
        db_session,
        title="Chainsaw Man",
        image_url="https://cdn.test/old.jpg",
    )

    updated = update_manga(db_session, manga, image_url="https://cdn.test/new.jpg")

    assert updated.image_url == "https://cdn.test/new.jpg"


def test_update_manga_keeps_an_image_url_the_caller_omits(
    db_session: Session,
) -> None:
    """`update_manga` skips None, so an omitted cover never clears the stored one."""
    manga = create_manga(
        db_session,
        title="Chainsaw Man",
        image_url="https://cdn.test/old.jpg",
    )

    updated = update_manga(db_session, manga, title="Chainsaw Man: Part 2")

    assert updated.image_url == "https://cdn.test/old.jpg"


def test_update_manga_with_no_args_changes_nothing(db_session: Session) -> None:
    manga = create_manga(db_session, title="Dandadan")

    updated = update_manga(db_session, manga)

    assert updated.title == "Dandadan"


def test_delete_manga_removes_the_row(db_session: Session) -> None:
    manga = create_manga(db_session, mal_id=3, title="Oyasumi Punpun")

    delete_manga(db_session, manga)

    assert get_manga_by_mal_id(db_session, 3) is None


def test_get_manga_by_source_external_id_returns_matching_manga(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Solo Leveling")
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
    manga_a = create_manga(db_session, title="Manga A")
    manga_b = create_manga(db_session, title="Manga B")
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


# --- get_manga_by_id ---


def test_get_manga_by_id_returns_matching_manga(db_session: Session) -> None:
    created = create_manga(db_session, title="Vinland Saga")

    found = get_manga_by_id(db_session, created.id)

    assert found is not None
    assert found.id == created.id


def test_get_manga_by_id_returns_none_when_missing(db_session: Session) -> None:
    assert get_manga_by_id(db_session, uuid.uuid4()) is None


def test_get_manga_by_id_eager_loads_authors(db_session: Session) -> None:
    """A lazy load here would cost one query per manga in a list response."""
    manga = create_manga(db_session, title="Blame!")
    assign_authors_to_manga(
        db_session, manga, [get_or_create_author(db_session, name="Tsutomu Nihei")]
    )
    db_session.expire_all()

    found = get_manga_by_id(db_session, manga.id)

    assert found is not None
    assert "authors" not in inspect(found).unloaded


# --- get_all_manga ---


def test_get_all_manga_orders_by_title(db_session: Session) -> None:
    for title in ("Chainsaw Man", "Akira", "Berserk"):
        create_manga(db_session, title=title)

    found = get_all_manga(db_session, limit=10, offset=0)

    assert [m.title for m in found] == ["Akira", "Berserk", "Chainsaw Man"]


def test_get_all_manga_pages_without_repeating_or_skipping(
    db_session: Session,
) -> None:
    """Offset paging is only stable when the query orders deterministically."""
    created = {create_manga(db_session, title=t).id for t in "ABCD"}

    first = get_all_manga(db_session, limit=2, offset=0)
    second = get_all_manga(db_session, limit=2, offset=2)

    assert len(first) == 2
    assert len(second) == 2
    assert {m.id for m in first}.isdisjoint({m.id for m in second})
    assert {m.id for m in first} | {m.id for m in second} == created


def test_get_all_manga_returns_empty_past_the_last_page(db_session: Session) -> None:
    create_manga(db_session, title="Solo Leveling")

    assert get_all_manga(db_session, limit=10, offset=10) == []


def test_get_all_manga_eager_loads_authors(db_session: Session) -> None:
    manga = create_manga(db_session, title="Pluto")
    assign_authors_to_manga(
        db_session, manga, [get_or_create_author(db_session, name="Naoki Urasawa")]
    )
    db_session.expire_all()

    found = get_all_manga(db_session, limit=10, offset=0)

    assert "authors" not in inspect(found[0]).unloaded


# --- count_manga ---


def test_count_manga_counts_every_row_not_only_a_page(db_session: Session) -> None:
    assert count_manga(db_session) == 0
    for title in ("Dorohedoro", "Gantz", "Homunculus"):
        create_manga(db_session, title=title)

    assert count_manga(db_session) == 3


# --- get_manga_tag_links ---


def _link_tag(
    db: Session,
    manga_id: uuid.UUID,
    name: str,
    *,
    rank: int | None,
    is_spoiler: bool = False,
) -> uuid.UUID:
    """Attach a tag to a manga and return the tag's ID."""
    tag = get_or_create_tag(db, name=name, category=None)
    bulk_add_tags_to_manga(
        db,
        [
            TagLinkValues(
                manga_id=manga_id, tag_id=tag.id, rank=rank, is_spoiler=is_spoiler
            )
        ],
    )
    return tag.id


def test_get_manga_tag_links_returns_the_link_attributes(db_session: Session) -> None:
    manga = create_manga(db_session, title="Monster")
    _link_tag(db_session, manga.id, "Psychological", rank=88, is_spoiler=True)

    links = get_manga_tag_links(db_session, manga.id)

    assert len(links) == 1
    assert links[0].tag.name == "Psychological"
    assert links[0].rank == 88
    assert links[0].is_spoiler is True


def test_get_manga_tag_links_orders_by_rank_descending(db_session: Session) -> None:
    manga = create_manga(db_session, title="20th Century Boys")
    _link_tag(db_session, manga.id, "Low", rank=10)
    _link_tag(db_session, manga.id, "High", rank=90)
    _link_tag(db_session, manga.id, "Middle", rank=50)

    links = get_manga_tag_links(db_session, manga.id)

    assert [link.tag.name for link in links] == ["High", "Middle", "Low"]


def test_get_manga_tag_links_sorts_an_unranked_tag_last(db_session: Session) -> None:
    """Postgres defaults DESC to NULLS FIRST, which would float unweighted tags up."""
    manga = create_manga(db_session, title="Oyasumi Punpun")
    _link_tag(db_session, manga.id, "Unranked", rank=None)
    _link_tag(db_session, manga.id, "Ranked", rank=5)

    links = get_manga_tag_links(db_session, manga.id)

    assert [link.tag.name for link in links] == ["Ranked", "Unranked"]


def test_get_manga_tag_links_does_not_cross_match(db_session: Session) -> None:
    manga_a = create_manga(db_session, title="Manga A")
    manga_b = create_manga(db_session, title="Manga B")
    _link_tag(db_session, manga_a.id, "Only On A", rank=1)
    _link_tag(db_session, manga_b.id, "Only On B", rank=1)

    links_a = get_manga_tag_links(db_session, manga_a.id)

    assert [link.tag.name for link in links_a] == ["Only On A"]


def test_get_manga_tag_links_returns_empty_for_an_untagged_manga(
    db_session: Session,
) -> None:
    manga = create_manga(db_session, title="Untagged")

    assert get_manga_tag_links(db_session, manga.id) == []


# --- get_manga_by_author_id ---


def _seed_manga_with_authors(db: Session, title: str, *author_names: str) -> uuid.UUID:
    """Create one manga credited to the named authors and return its ID."""
    manga = create_manga(db, title=title)
    assign_authors_to_manga(
        db, manga, [get_or_create_author(db, name=name) for name in author_names]
    )
    return manga.id


def test_get_manga_by_author_id_returns_only_that_authors_manga(
    db_session: Session,
) -> None:
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    _seed_manga_with_authors(db_session, "Berserk", "Kentaro Miura")
    _seed_manga_with_authors(db_session, "Monster", "Naoki Urasawa")

    found = get_manga_by_author_id(db_session, miura.id, limit=10, offset=0)

    assert [m.title for m in found] == ["Berserk"]


def test_get_manga_by_author_id_returns_a_co_authored_manga_once(
    db_session: Session,
) -> None:
    """The join must not multiply a manga by its number of authors."""
    obata = get_or_create_author(db_session, name="Takeshi Obata")
    _seed_manga_with_authors(db_session, "Death Note", "Takeshi Obata", "Tsugumi Ohba")

    found = get_manga_by_author_id(db_session, obata.id, limit=10, offset=0)

    assert len(found) == 1
    assert sorted(a.name for a in found[0].authors) == [
        "Takeshi Obata",
        "Tsugumi Ohba",
    ]


def test_get_manga_by_author_id_orders_by_title(db_session: Session) -> None:
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    for title in ("Gigantomakhia", "Berserk", "Duranki"):
        _seed_manga_with_authors(db_session, title, "Kentaro Miura")

    found = get_manga_by_author_id(db_session, miura.id, limit=10, offset=0)

    assert [m.title for m in found] == ["Berserk", "Duranki", "Gigantomakhia"]


def test_get_manga_by_author_id_pages_without_repeating_or_skipping(
    db_session: Session,
) -> None:
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    created = {
        _seed_manga_with_authors(db_session, title, "Kentaro Miura")
        for title in ("Berserk", "Duranki", "Gigantomakhia", "Japan")
    }

    first = get_manga_by_author_id(db_session, miura.id, limit=2, offset=0)
    second = get_manga_by_author_id(db_session, miura.id, limit=2, offset=2)

    assert {m.id for m in first}.isdisjoint({m.id for m in second})
    assert {m.id for m in first} | {m.id for m in second} == created


def test_get_manga_by_author_id_pages_when_titles_are_equal(
    db_session: Session,
) -> None:
    """Equal titles need the ID tiebreaker to give a total order."""
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    created = {
        _seed_manga_with_authors(db_session, "Same Title", "Kentaro Miura")
        for _ in range(4)
    }

    first = get_manga_by_author_id(db_session, miura.id, limit=2, offset=0)
    second = get_manga_by_author_id(db_session, miura.id, limit=2, offset=2)

    assert {m.id for m in first}.isdisjoint({m.id for m in second})
    assert {m.id for m in first} | {m.id for m in second} == created


def test_get_manga_by_author_id_returns_empty_for_an_author_with_no_manga(
    db_session: Session,
) -> None:
    author = get_or_create_author(db_session, name="Unpublished Author")

    assert get_manga_by_author_id(db_session, author.id, limit=10, offset=0) == []


def test_get_manga_by_author_id_returns_empty_for_an_unknown_author(
    db_session: Session,
) -> None:
    assert get_manga_by_author_id(db_session, uuid.uuid4(), limit=10, offset=0) == []


def test_get_manga_by_author_id_eager_loads_authors(db_session: Session) -> None:
    """A lazy load here would cost one query per manga in the page."""
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    _seed_manga_with_authors(db_session, "Berserk", "Kentaro Miura")
    db_session.expire_all()

    found = get_manga_by_author_id(db_session, miura.id, limit=10, offset=0)

    assert "authors" not in inspect(found[0]).unloaded


# --- count_manga_by_author_id ---


def test_count_manga_by_author_id_counts_every_credit_not_only_a_page(
    db_session: Session,
) -> None:
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    for title in ("Berserk", "Duranki", "Gigantomakhia"):
        _seed_manga_with_authors(db_session, title, "Kentaro Miura")

    assert count_manga_by_author_id(db_session, miura.id) == 3


def test_count_manga_by_author_id_ignores_other_authors_manga(
    db_session: Session,
) -> None:
    miura = get_or_create_author(db_session, name="Kentaro Miura")
    _seed_manga_with_authors(db_session, "Berserk", "Kentaro Miura")
    _seed_manga_with_authors(db_session, "Monster", "Naoki Urasawa")

    assert count_manga_by_author_id(db_session, miura.id) == 1


def test_count_manga_by_author_id_counts_a_co_authored_manga_once(
    db_session: Session,
) -> None:
    obata = get_or_create_author(db_session, name="Takeshi Obata")
    _seed_manga_with_authors(db_session, "Death Note", "Takeshi Obata", "Tsugumi Ohba")

    assert count_manga_by_author_id(db_session, obata.id) == 1


def test_count_manga_by_author_id_returns_zero_for_an_unknown_author(
    db_session: Session,
) -> None:
    assert count_manga_by_author_id(db_session, uuid.uuid4()) == 0


# --- get_manga_by_tag_id ---


def _seed_manga_with_tags(db: Session, title: str, *tag_names: str) -> uuid.UUID:
    """Create one manga carrying the named tags and return its ID."""
    manga = create_manga(db, title=title)
    for name in tag_names:
        _link_tag(db, manga.id, name, rank=None)
    return manga.id


def test_get_manga_by_tag_id_returns_only_manga_with_that_tag(
    db_session: Session,
) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    _seed_manga_with_tags(db_session, "Berserk", "Action")
    _seed_manga_with_tags(db_session, "Monster", "Psychological")

    found = get_manga_by_tag_id(db_session, action.id, limit=10, offset=0)

    assert [m.title for m in found] == ["Berserk"]


def test_get_manga_by_tag_id_returns_a_multi_tagged_manga_once(
    db_session: Session,
) -> None:
    """The join must not multiply a manga by its other tags."""
    action = get_or_create_tag(db_session, name="Action", category=None)
    _seed_manga_with_tags(db_session, "Berserk", "Action", "Seinen", "Tragedy")

    found = get_manga_by_tag_id(db_session, action.id, limit=10, offset=0)

    assert len(found) == 1


def test_get_manga_by_tag_id_orders_by_title(db_session: Session) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    for title in ("Gigantomakhia", "Berserk", "Duranki"):
        _seed_manga_with_tags(db_session, title, "Action")

    found = get_manga_by_tag_id(db_session, action.id, limit=10, offset=0)

    assert [m.title for m in found] == ["Berserk", "Duranki", "Gigantomakhia"]


def test_get_manga_by_tag_id_pages_without_repeating_or_skipping(
    db_session: Session,
) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    created = {
        _seed_manga_with_tags(db_session, title, "Action")
        for title in ("Berserk", "Duranki", "Gigantomakhia", "Japan")
    }

    first = get_manga_by_tag_id(db_session, action.id, limit=2, offset=0)
    second = get_manga_by_tag_id(db_session, action.id, limit=2, offset=2)

    assert {m.id for m in first}.isdisjoint({m.id for m in second})
    assert {m.id for m in first} | {m.id for m in second} == created


def test_get_manga_by_tag_id_pages_when_titles_are_equal(db_session: Session) -> None:
    """Equal titles need the ID tiebreaker to give a total order."""
    action = get_or_create_tag(db_session, name="Action", category=None)
    created = {
        _seed_manga_with_tags(db_session, "Same Title", "Action") for _ in range(4)
    }

    first = get_manga_by_tag_id(db_session, action.id, limit=2, offset=0)
    second = get_manga_by_tag_id(db_session, action.id, limit=2, offset=2)

    assert {m.id for m in first}.isdisjoint({m.id for m in second})
    assert {m.id for m in first} | {m.id for m in second} == created


def test_get_manga_by_tag_id_returns_empty_for_a_tag_on_no_manga(
    db_session: Session,
) -> None:
    tag = get_or_create_tag(db_session, name="Unused", category=None)

    assert get_manga_by_tag_id(db_session, tag.id, limit=10, offset=0) == []


def test_get_manga_by_tag_id_returns_empty_for_an_unknown_tag(
    db_session: Session,
) -> None:
    assert get_manga_by_tag_id(db_session, uuid.uuid4(), limit=10, offset=0) == []


def test_get_manga_by_tag_id_eager_loads_authors(db_session: Session) -> None:
    """A lazy load here would cost one query per manga in the page."""
    action = get_or_create_tag(db_session, name="Action", category=None)
    manga = create_manga(db_session, title="Berserk")
    assign_authors_to_manga(
        db_session, manga, [get_or_create_author(db_session, name="Kentaro Miura")]
    )
    _link_tag(db_session, manga.id, "Action", rank=None)
    db_session.expire_all()

    found = get_manga_by_tag_id(db_session, action.id, limit=10, offset=0)

    assert "authors" not in inspect(found[0]).unloaded


# --- count_manga_by_tag_id ---


def test_count_manga_by_tag_id_counts_every_manga_not_only_a_page(
    db_session: Session,
) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    for title in ("Berserk", "Duranki", "Gigantomakhia"):
        _seed_manga_with_tags(db_session, title, "Action")

    assert count_manga_by_tag_id(db_session, action.id) == 3


def test_count_manga_by_tag_id_ignores_manga_without_the_tag(
    db_session: Session,
) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    _seed_manga_with_tags(db_session, "Berserk", "Action")
    _seed_manga_with_tags(db_session, "Monster", "Psychological")

    assert count_manga_by_tag_id(db_session, action.id) == 1


def test_count_manga_by_tag_id_counts_a_multi_tagged_manga_once(
    db_session: Session,
) -> None:
    action = get_or_create_tag(db_session, name="Action", category=None)
    _seed_manga_with_tags(db_session, "Berserk", "Action", "Seinen", "Tragedy")

    assert count_manga_by_tag_id(db_session, action.id) == 1


def test_count_manga_by_tag_id_returns_zero_for_an_unknown_tag(
    db_session: Session,
) -> None:
    assert count_manga_by_tag_id(db_session, uuid.uuid4()) == 0
