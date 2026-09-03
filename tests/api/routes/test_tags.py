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


def _seed_tag(db: Session, name: str, category: str | None = "Theme") -> uuid.UUID:
    """Create the named tag, or reuse it, and return its ID."""
    return get_or_create_tag(db, name=name, category=category).id


def _seed_manga(
    db: Session,
    *,
    title: str,
    tags: tuple[str, ...] = (),
    authors: tuple[str, ...] = (),
    status: MangaStatus | None = MangaStatus.FINISHED,
    image_url: str | None = "https://cdn.test/cover.jpg",
) -> uuid.UUID:
    """Create one manga carrying the named tags and authors, and return its ID."""
    manga = create_manga(db, title=title, status=status, image_url=image_url)
    if authors:
        assign_authors_to_manga(
            db, manga, [get_or_create_author(db, name=name) for name in authors]
        )
    if tags:
        bulk_add_tags_to_manga(
            db,
            [
                TagLinkValues(
                    manga_id=manga.id,
                    tag_id=_seed_tag(db, name),
                    rank=None,
                    is_spoiler=False,
                )
                for name in tags
            ],
        )
    return manga.id


class TestListTags:
    def test_returns_a_page_of_summaries(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Psychological")

        response = client.get("/tags")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["limit"] == 20
        assert body["offset"] == 0
        assert body["items"] == [{"id": str(tag_id), "name": "Psychological"}]

    def test_omits_detail_only_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """manga_count costs a query per row, so it belongs to the detail only."""
        _seed_tag(db_session, "Psychological")

        item = client.get("/tags").json()["items"][0]

        assert "manga_count" not in item
        assert "category" not in item

    def test_orders_tags_by_name(self, client: TestClient, db_session: Session) -> None:
        for name in ("Seinen", "Action", "Mecha"):
            _seed_tag(db_session, name)

        items = client.get("/tags").json()["items"]

        assert [t["name"] for t in items] == ["Action", "Mecha", "Seinen"]

    def test_total_counts_rows_beyond_the_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        for name in ("Action", "Mecha", "Seinen"):
            _seed_tag(db_session, name)

        body = client.get("/tags", params={"limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_total_is_zero_when_no_tag_exists(self, client: TestClient) -> None:
        body = client.get("/tags").json()

        assert body["items"] == []
        assert body["total"] == 0

    def test_pages_do_not_overlap(
        self, client: TestClient, db_session: Session
    ) -> None:
        for name in ("Action", "Mecha", "Seinen", "Tragedy"):
            _seed_tag(db_session, name)

        first = client.get("/tags", params={"limit": 2, "offset": 0}).json()
        second = client.get("/tags", params={"limit": 2, "offset": 2}).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_rejects_a_limit_above_the_maximum(self, client: TestClient) -> None:
        assert client.get("/tags", params={"limit": 101}).status_code == 422

    def test_rejects_a_limit_below_one(self, client: TestClient) -> None:
        assert client.get("/tags", params={"limit": 0}).status_code == 422

    def test_rejects_a_negative_offset(self, client: TestClient) -> None:
        assert client.get("/tags", params={"offset": -1}).status_code == 422


class TestGetTag:
    def test_returns_the_full_record(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Psychological", "Theme")
        _seed_manga(db_session, title="Monster", tags=("Psychological",))

        response = client.get(f"/tags/{tag_id}")

        assert response.status_code == 200
        assert response.json() == {
            "id": str(tag_id),
            "name": "Psychological",
            "category": "Theme",
            "manga_count": 1,
        }

    def test_returns_a_null_category(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Uncategorised", None)

        assert client.get(f"/tags/{tag_id}").json()["category"] is None

    def test_does_not_embed_the_manga_themselves(
        self, client: TestClient, db_session: Session
    ) -> None:
        """One tag can hold thousands of manga, so they are their own endpoint."""
        tag_id = _seed_tag(db_session, "Action")
        _seed_manga(db_session, title="Berserk", tags=("Action",))

        assert "manga" not in client.get(f"/tags/{tag_id}").json()

    def test_counts_only_the_manga_carrying_that_tag(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        _seed_manga(db_session, title="Berserk", tags=("Action",))
        _seed_manga(db_session, title="Monster", tags=("Psychological",))

        assert client.get(f"/tags/{tag_id}").json()["manga_count"] == 1

    def test_counts_zero_for_a_tag_on_no_manga(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Unused")

        assert client.get(f"/tags/{tag_id}").json()["manga_count"] == 0

    def test_returns_404_for_an_unknown_id(self, client: TestClient) -> None:
        response = client.get(f"/tags/{uuid.uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_returns_422_for_a_malformed_id(self, client: TestClient) -> None:
        assert client.get("/tags/not-a-uuid").status_code == 422


class TestListTaggedManga:
    def test_returns_the_manga_carrying_the_tag(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        _seed_manga(
            db_session,
            title="Berserk",
            tags=("Action",),
            authors=("Kentaro Miura",),
        )

        response = client.get(f"/tags/{tag_id}/manga")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Berserk"
        assert body["items"][0]["status"] == "finished"
        assert [a["name"] for a in body["items"][0]["authors"]] == ["Kentaro Miura"]

    def test_excludes_manga_without_the_tag(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        _seed_manga(db_session, title="Berserk", tags=("Action",))
        _seed_manga(db_session, title="Monster", tags=("Psychological",))

        items = client.get(f"/tags/{tag_id}/manga").json()["items"]

        assert [m["title"] for m in items] == ["Berserk"]

    def test_lists_a_multi_tagged_manga_once(
        self, client: TestClient, db_session: Session
    ) -> None:
        """The join must not multiply a manga by its other tags."""
        tag_id = _seed_tag(db_session, "Action")
        _seed_manga(
            db_session,
            title="Berserk",
            tags=("Action", "Seinen", "Tragedy"),
        )

        body = client.get(f"/tags/{tag_id}/manga").json()

        assert body["total"] == 1
        assert len(body["items"]) == 1

    def test_orders_manga_by_title(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        for title in ("Gigantomakhia", "Berserk", "Duranki"):
            _seed_manga(db_session, title=title, tags=("Action",))

        items = client.get(f"/tags/{tag_id}/manga").json()["items"]

        assert [m["title"] for m in items] == ["Berserk", "Duranki", "Gigantomakhia"]

    def test_total_counts_rows_beyond_the_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        for title in ("Berserk", "Duranki", "Gigantomakhia"):
            _seed_manga(db_session, title=title, tags=("Action",))

        body = client.get(f"/tags/{tag_id}/manga", params={"limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_pages_do_not_overlap(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        for title in ("Berserk", "Duranki", "Gigantomakhia", "Japan"):
            _seed_manga(db_session, title=title, tags=("Action",))

        params = {"limit": 2, "offset": 0}
        first = client.get(f"/tags/{tag_id}/manga", params=params).json()
        params = {"limit": 2, "offset": 2}
        second = client.get(f"/tags/{tag_id}/manga", params=params).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_pages_do_not_overlap_when_titles_are_equal(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Equal titles need the ID tiebreaker to give a total order."""
        tag_id = _seed_tag(db_session, "Action")
        for _ in range(4):
            _seed_manga(db_session, title="Same Title", tags=("Action",))

        params = {"limit": 2, "offset": 0}
        first = client.get(f"/tags/{tag_id}/manga", params=params).json()
        params = {"limit": 2, "offset": 2}
        second = client.get(f"/tags/{tag_id}/manga", params=params).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_total_matches_the_count_on_the_tag_detail(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")
        for title in ("Berserk", "Duranki"):
            _seed_manga(db_session, title=title, tags=("Action",))

        detail = client.get(f"/tags/{tag_id}").json()
        page = client.get(f"/tags/{tag_id}/manga").json()

        assert detail["manga_count"] == page["total"]

    def test_returns_an_empty_page_for_a_tag_on_no_manga(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Unused")

        body = client.get(f"/tags/{tag_id}/manga").json()

        assert body["items"] == []
        assert body["total"] == 0

    def test_returns_an_empty_page_for_an_unknown_tag(self, client: TestClient) -> None:
        """An unknown tag's manga collection is empty, not missing."""
        response = client.get(f"/tags/{uuid.uuid4()}/manga")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_rejects_a_limit_above_the_maximum(
        self, client: TestClient, db_session: Session
    ) -> None:
        tag_id = _seed_tag(db_session, "Action")

        response = client.get(f"/tags/{tag_id}/manga", params={"limit": 101})

        assert response.status_code == 422

    def test_returns_422_for_a_malformed_id(self, client: TestClient) -> None:
        assert client.get("/tags/not-a-uuid/manga").status_code == 422
