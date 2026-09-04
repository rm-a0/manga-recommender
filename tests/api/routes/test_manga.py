import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.db.repositories.authors import get_or_create_author
from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    assign_authors_to_manga,
    bulk_add_tags_to_manga,
    create_manga,
)
from manga_recommender.db.repositories.tags import get_or_create_tag


def _seed_manga(
    db: Session,
    *,
    title: str = "Berserk",
    author: str | None = "Kentaro Miura",
    status: MangaStatus | None = MangaStatus.HIATUS,
    image_url: str | None = "https://cdn.test/berserk.jpg",
    description: str | None = "A lone swordsman.",
) -> uuid.UUID:
    """Create one manga, optionally with an author, and return its ID."""
    manga = create_manga(
        db,
        title=title,
        status=status,
        image_url=image_url,
        description=description,
    )
    if author is not None:
        assign_authors_to_manga(db, manga, [get_or_create_author(db, name=author)])
    return manga.id


def _tag_manga(
    db: Session,
    manga_id: uuid.UUID,
    name: str,
    *,
    rank: int | None,
    is_spoiler: bool = False,
) -> None:
    """Attach one tag to a manga."""
    tag = get_or_create_tag(db, name=name, category=None)
    bulk_add_tags_to_manga(
        db,
        [
            TagLinkValues(
                manga_id=manga_id, tag_id=tag.id, rank=rank, is_spoiler=is_spoiler
            )
        ],
    )


class TestListManga:
    def test_returns_a_page_of_summaries(
        self, client: TestClient, db_session: Session
    ) -> None:
        _seed_manga(db_session)

        response = client.get("/manga")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["limit"] == 20
        assert body["offset"] == 0
        assert body["items"][0]["title"] == "Berserk"
        assert body["items"][0]["status"] == "hiatus"
        assert [a["name"] for a in body["items"][0]["authors"]] == ["Kentaro Miura"]

    def test_omits_detail_only_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """A list item must stay cheap; description and tags belong to the detail."""
        _seed_manga(db_session)

        item = client.get("/manga").json()["items"][0]

        assert "description" not in item
        assert "tags" not in item

    def test_serializes_a_manga_with_no_optional_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Every nullable column must serialize, not raise on the way out."""
        _seed_manga(
            db_session,
            title="Sparse",
            author=None,
            status=None,
            image_url=None,
            description=None,
        )

        response = client.get("/manga")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["status"] is None
        assert item["image_url"] is None
        assert item["authors"] == []

    def test_total_counts_rows_beyond_the_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        for title in ("Akira", "Berserk", "Claymore"):
            _seed_manga(db_session, title=title, author=None)

        body = client.get("/manga", params={"limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_pages_do_not_overlap(
        self, client: TestClient, db_session: Session
    ) -> None:
        for title in ("Akira", "Berserk", "Claymore", "Dorohedoro"):
            _seed_manga(db_session, title=title, author=None)

        first = client.get("/manga", params={"limit": 2, "offset": 0}).json()
        second = client.get("/manga", params={"limit": 2, "offset": 2}).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_searches_titles_with_q(
        self, client: TestClient, db_session: Session
    ) -> None:
        _seed_manga(db_session, title="Berserk", author=None)
        _seed_manga(db_session, title="Monster", author=None)

        body = client.get("/manga", params={"q": "berserk"}).json()

        assert [item["title"] for item in body["items"]] == ["Berserk"]

    def test_requires_every_word_of_q(
        self, client: TestClient, db_session: Session
    ) -> None:
        """The query splits on whitespace, so `attack titan` finds the gap title."""
        _seed_manga(db_session, title="Attack on Titan", author=None)
        _seed_manga(db_session, title="Titan Junior High", author=None)

        body = client.get("/manga", params={"q": "attack titan"}).json()

        assert [item["title"] for item in body["items"]] == ["Attack on Titan"]

    def test_total_counts_only_the_search_matches(
        self, client: TestClient, db_session: Session
    ) -> None:
        for title in ("Berserk", "Berserk Gaiden", "Monster"):
            _seed_manga(db_session, title=title, author=None)

        body = client.get("/manga", params={"q": "berserk", "limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 2

    def test_ignores_a_whitespace_only_q(
        self, client: TestClient, db_session: Session
    ) -> None:
        _seed_manga(db_session, title="Berserk", author=None)

        body = client.get("/manga", params={"q": "   "}).json()

        assert body["total"] == 1

    def test_rejects_a_q_below_the_minimum_length(self, client: TestClient) -> None:
        assert client.get("/manga", params={"q": "a"}).status_code == 422

    def test_rejects_a_limit_above_the_maximum(self, client: TestClient) -> None:
        assert client.get("/manga", params={"limit": 101}).status_code == 422

    def test_rejects_a_limit_below_one(self, client: TestClient) -> None:
        assert client.get("/manga", params={"limit": 0}).status_code == 422

    def test_rejects_a_negative_offset(self, client: TestClient) -> None:
        assert client.get("/manga", params={"offset": -1}).status_code == 422


class TestGetManga:
    def test_returns_the_full_record(
        self, client: TestClient, db_session: Session
    ) -> None:
        manga_id = _seed_manga(db_session)

        response = client.get(f"/manga/{manga_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(manga_id)
        assert body["title"] == "Berserk"
        assert body["description"] == "A lone swordsman."
        assert [a["name"] for a in body["authors"]] == ["Kentaro Miura"]

    def test_includes_the_rank_and_spoiler_flag_of_each_tag(
        self, client: TestClient, db_session: Session
    ) -> None:
        manga_id = _seed_manga(db_session)
        _tag_manga(db_session, manga_id, "Dark Fantasy", rank=90)
        _tag_manga(db_session, manga_id, "Major Death", rank=50, is_spoiler=True)

        tags = client.get(f"/manga/{manga_id}").json()["tags"]

        assert [t["name"] for t in tags] == ["Dark Fantasy", "Major Death"]
        assert tags[0] == {
            "id": tags[0]["id"],
            "name": "Dark Fantasy",
            "is_spoiler": False,
            "rank": 90,
        }
        assert tags[1]["is_spoiler"] is True

    def test_lists_an_unranked_tag_last(
        self, client: TestClient, db_session: Session
    ) -> None:
        manga_id = _seed_manga(db_session)
        _tag_manga(db_session, manga_id, "Unranked", rank=None)
        _tag_manga(db_session, manga_id, "Ranked", rank=5)

        tags = client.get(f"/manga/{manga_id}").json()["tags"]

        assert [t["name"] for t in tags] == ["Ranked", "Unranked"]

    def test_returns_an_empty_tag_list_for_an_untagged_manga(
        self, client: TestClient, db_session: Session
    ) -> None:
        manga_id = _seed_manga(db_session)

        assert client.get(f"/manga/{manga_id}").json()["tags"] == []

    def test_returns_404_for_an_unknown_id(self, client: TestClient) -> None:
        response = client.get(f"/manga/{uuid.uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_returns_422_for_a_malformed_id(self, client: TestClient) -> None:
        assert client.get("/manga/not-a-uuid").status_code == 422
