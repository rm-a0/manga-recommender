import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.db.repositories.authors import get_or_create_author
from manga_recommender.db.repositories.manga import (
    assign_authors_to_manga,
    create_manga,
)


def _seed_author(db: Session, name: str) -> uuid.UUID:
    """Create the named author, or reuse it, and return its ID."""
    return get_or_create_author(db, name=name).id


def _seed_manga(
    db: Session,
    *,
    title: str,
    authors: tuple[str, ...] = (),
    status: MangaStatus | None = MangaStatus.FINISHED,
    image_url: str | None = "https://cdn.test/cover.jpg",
) -> uuid.UUID:
    """Create one manga credited to the named authors, and return its ID."""
    manga = create_manga(db, title=title, status=status, image_url=image_url)
    if authors:
        assign_authors_to_manga(
            db, manga, [get_or_create_author(db, name=name) for name in authors]
        )
    return manga.id


class TestListAuthors:
    def test_returns_a_page_of_summaries(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")

        response = client.get("/authors")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["limit"] == 20
        assert body["offset"] == 0
        assert body["items"] == [{"id": str(author_id), "name": "Kentaro Miura"}]

    def test_omits_detail_only_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """manga_count costs a query per row, so it belongs to the detail only."""
        _seed_author(db_session, "Kentaro Miura")

        item = client.get("/authors").json()["items"][0]

        assert "manga_count" not in item

    def test_orders_authors_by_name(
        self, client: TestClient, db_session: Session
    ) -> None:
        for name in ("Naoki Urasawa", "Akira Toriyama", "Junji Ito"):
            _seed_author(db_session, name)

        items = client.get("/authors").json()["items"]

        assert [a["name"] for a in items] == [
            "Akira Toriyama",
            "Junji Ito",
            "Naoki Urasawa",
        ]

    def test_total_counts_rows_beyond_the_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        for name in ("Akira Toriyama", "Junji Ito", "Naoki Urasawa"):
            _seed_author(db_session, name)

        body = client.get("/authors", params={"limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_pages_do_not_overlap(
        self, client: TestClient, db_session: Session
    ) -> None:
        for name in ("Akira Toriyama", "Junji Ito", "Naoki Urasawa", "Q Hayashida"):
            _seed_author(db_session, name)

        first = client.get("/authors", params={"limit": 2, "offset": 0}).json()
        second = client.get("/authors", params={"limit": 2, "offset": 2}).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_rejects_a_limit_above_the_maximum(self, client: TestClient) -> None:
        assert client.get("/authors", params={"limit": 101}).status_code == 422

    def test_rejects_a_limit_below_one(self, client: TestClient) -> None:
        assert client.get("/authors", params={"limit": 0}).status_code == 422

    def test_rejects_a_negative_offset(self, client: TestClient) -> None:
        assert client.get("/authors", params={"offset": -1}).status_code == 422


class TestGetAuthor:
    def test_returns_the_full_record(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        _seed_manga(db_session, title="Berserk", authors=("Kentaro Miura",))

        response = client.get(f"/authors/{author_id}")

        assert response.status_code == 200
        assert response.json() == {
            "id": str(author_id),
            "name": "Kentaro Miura",
            "manga_count": 1,
        }

    def test_does_not_embed_the_manga_themselves(
        self, client: TestClient, db_session: Session
    ) -> None:
        """One author can credit hundreds of manga, so they are their own endpoint."""
        author_id = _seed_author(db_session, "Kentaro Miura")
        _seed_manga(db_session, title="Berserk", authors=("Kentaro Miura",))

        body = client.get(f"/authors/{author_id}").json()

        assert "manga" not in body

    def test_counts_only_the_manga_credited_to_that_author(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        _seed_manga(db_session, title="Berserk", authors=("Kentaro Miura",))
        _seed_manga(db_session, title="Monster", authors=("Naoki Urasawa",))

        assert client.get(f"/authors/{author_id}").json()["manga_count"] == 1

    def test_counts_a_co_authored_manga_once(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Takeshi Obata")
        _seed_manga(
            db_session,
            title="Death Note",
            authors=("Takeshi Obata", "Tsugumi Ohba"),
        )

        assert client.get(f"/authors/{author_id}").json()["manga_count"] == 1

    def test_counts_zero_for_an_author_with_no_manga(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Unpublished Author")

        assert client.get(f"/authors/{author_id}").json()["manga_count"] == 0

    def test_returns_404_for_an_unknown_id(self, client: TestClient) -> None:
        response = client.get(f"/authors/{uuid.uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_returns_422_for_a_malformed_id(self, client: TestClient) -> None:
        assert client.get("/authors/not-a-uuid").status_code == 422


class TestListAuthorManga:
    def test_returns_the_manga_credited_to_the_author(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        _seed_manga(db_session, title="Berserk", authors=("Kentaro Miura",))

        response = client.get(f"/authors/{author_id}/manga")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Berserk"
        assert body["items"][0]["status"] == "finished"

    def test_excludes_manga_by_other_authors(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        _seed_manga(db_session, title="Berserk", authors=("Kentaro Miura",))
        _seed_manga(db_session, title="Monster", authors=("Naoki Urasawa",))

        items = client.get(f"/authors/{author_id}/manga").json()["items"]

        assert [m["title"] for m in items] == ["Berserk"]

    def test_lists_a_co_authored_manga_once_with_every_author(
        self, client: TestClient, db_session: Session
    ) -> None:
        """A manga with two authors is one item carrying both, not one item each."""
        author_id = _seed_author(db_session, "Takeshi Obata")
        _seed_manga(
            db_session,
            title="Death Note",
            authors=("Takeshi Obata", "Tsugumi Ohba"),
        )

        body = client.get(f"/authors/{author_id}/manga").json()

        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert sorted(a["name"] for a in body["items"][0]["authors"]) == [
            "Takeshi Obata",
            "Tsugumi Ohba",
        ]

    def test_orders_manga_by_title(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        for title in ("Gigantomakhia", "Berserk", "Duranki"):
            _seed_manga(db_session, title=title, authors=("Kentaro Miura",))

        items = client.get(f"/authors/{author_id}/manga").json()["items"]

        assert [m["title"] for m in items] == ["Berserk", "Duranki", "Gigantomakhia"]

    def test_total_counts_rows_beyond_the_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        for title in ("Berserk", "Duranki", "Gigantomakhia"):
            _seed_manga(db_session, title=title, authors=("Kentaro Miura",))

        body = client.get(f"/authors/{author_id}/manga", params={"limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_pages_do_not_overlap(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        for title in ("Berserk", "Duranki", "Gigantomakhia", "Japan"):
            _seed_manga(db_session, title=title, authors=("Kentaro Miura",))

        params = {"limit": 2, "offset": 0}
        first = client.get(f"/authors/{author_id}/manga", params=params).json()
        params = {"limit": 2, "offset": 2}
        second = client.get(f"/authors/{author_id}/manga", params=params).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_pages_do_not_overlap_when_titles_are_equal(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Equal titles need the ID tiebreaker to give a total order."""
        author_id = _seed_author(db_session, "Kentaro Miura")
        for _ in range(4):
            _seed_manga(db_session, title="Same Title", authors=("Kentaro Miura",))

        params = {"limit": 2, "offset": 0}
        first = client.get(f"/authors/{author_id}/manga", params=params).json()
        params = {"limit": 2, "offset": 2}
        second = client.get(f"/authors/{author_id}/manga", params=params).json()

        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 4

    def test_total_matches_the_count_on_the_author_detail(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")
        for title in ("Berserk", "Duranki"):
            _seed_manga(db_session, title=title, authors=("Kentaro Miura",))

        detail = client.get(f"/authors/{author_id}").json()
        page = client.get(f"/authors/{author_id}/manga").json()

        assert detail["manga_count"] == page["total"]

    def test_returns_an_empty_page_for_an_author_with_no_manga(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Unpublished Author")

        body = client.get(f"/authors/{author_id}/manga").json()

        assert body["items"] == []
        assert body["total"] == 0

    def test_returns_an_empty_page_for_an_unknown_author(
        self, client: TestClient
    ) -> None:
        """An unknown author's manga collection is empty, not missing."""
        response = client.get(f"/authors/{uuid.uuid4()}/manga")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_rejects_a_limit_above_the_maximum(
        self, client: TestClient, db_session: Session
    ) -> None:
        author_id = _seed_author(db_session, "Kentaro Miura")

        response = client.get(f"/authors/{author_id}/manga", params={"limit": 101})

        assert response.status_code == 422

    def test_returns_422_for_a_malformed_id(self, client: TestClient) -> None:
        assert client.get("/authors/not-a-uuid/manga").status_code == 422
