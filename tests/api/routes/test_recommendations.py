"""Tests for the recommendation routes."""

import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga, MangaType
from manga_recommender.db.repositories.manga_metrics import create_manga_metric


def _post(client: TestClient, **body: Any) -> Any:
    """Send one recommendation request and return the response."""
    return client.post("/recommendations", json=body)


def _titles(payload: dict[str, Any]) -> list[str]:
    """Return the title of every recommended manga, in response order."""
    return [item["manga"]["title"] for item in payload["recommendations"]]


class TestListStrategies:
    def test_returns_every_strategy_with_its_weights(self, client: TestClient) -> None:
        response = client.get("/recommendations/strategies")

        assert response.status_code == 200
        by_name = {row["strategy"]: row["weights"] for row in response.json()}
        assert by_name["content"] == {"content": 1.0}
        assert by_name["tags"] == {"tags": 1.0}
        assert set(by_name) == {"auto", "balanced", "content", "tags"}

    def test_names_only_sources_the_registry_knows(self, client: TestClient) -> None:
        from manga_recommender.recommender.registry import get_source_names

        response = client.get("/recommendations/strategies")

        for row in response.json():
            assert set(row["weights"]) <= get_source_names()


class TestRecommendManga:
    def test_returns_the_nearest_manga_first(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Near", 5)
        embedded_manga("Far", 60)

        response = _post(client, liked_ids=[str(seed.id)], strategy="content")

        assert response.status_code == 200
        assert _titles(response.json()) == ["Near", "Far"]

    def test_leaves_the_liked_manga_out_of_the_recommendations(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Near", 5)

        response = _post(client, liked_ids=[str(seed.id)], strategy="content")

        assert "Seed" not in _titles(response.json())

    def test_names_the_seed_of_every_reason(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Near", 5)

        payload = _post(client, liked_ids=[str(seed.id)], strategy="content").json()

        reasons = payload["recommendations"][0]["reasons"]
        assert reasons == [{"source": "content", "seed_id": str(seed.id)}]

    def test_echoes_each_seed_with_its_title(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Near", 5)

        payload = _post(client, liked_ids=[str(seed.id)], strategy="content").json()

        assert payload["seeds"] == [{"id": str(seed.id), "title": "Seed"}]

    def test_echoes_the_strategy_that_ran(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)

        payload = _post(client, liked_ids=[str(seed.id)], strategy="tags").json()

        assert payload["strategy"] == "tags"

    def test_leaves_out_a_seed_that_matches_no_manga(self, client: TestClient) -> None:
        payload = _post(client, liked_ids=[str(uuid.uuid4())]).json()

        assert payload["seeds"] == []
        assert payload["recommendations"] == []

    def test_returns_at_most_the_requested_limit(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        for degrees in (5, 10, 15):
            embedded_manga(f"Match {degrees}", degrees)

        payload = _post(
            client, liked_ids=[str(seed.id)], strategy="content", limit=2
        ).json()

        assert len(payload["recommendations"]) == 2

    def test_drops_a_manga_the_request_excludes_by_id(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        near = embedded_manga("Near", 5)
        embedded_manga("Far", 60)

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            exclude_ids=[str(near.id)],
            strategy="content",
        ).json()

        assert _titles(payload) == ["Far"]

    def test_drops_a_manga_that_carries_an_excluded_tag(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
        tag_manga: Callable[[uuid.UUID, str], None],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        near = embedded_manga("Near", 5)
        embedded_manga("Far", 60)
        tag_manga(near.id, "ecchi")

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            exclude_tags=["ecchi"],
            strategy="content",
        ).json()

        assert _titles(payload) == ["Far"]

    def test_weights_add_a_source_to_the_strategy(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
        plain_manga: Callable[[str], Manga],
        tag_manga: Callable[[uuid.UUID, str], None],
    ) -> None:
        """The override merges onto the strategy, it does not replace it."""
        seed = embedded_manga("Seed", 0)
        embedded_manga("By Vector", 5)
        by_tag = plain_manga("By Tag")
        tag_manga(seed.id, "action")
        tag_manga(by_tag.id, "action")

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            strategy="content",
            weights={"tags": 1.0},
        ).json()

        assert set(_titles(payload)) == {"By Vector", "By Tag"}

    def test_applies_the_requested_dislike_cutoff(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        """cos(30) is about 0.866: kept at the default 0.9, dropped at 0.8."""
        seed = embedded_manga("Seed", 0)
        disliked = embedded_manga("Disliked", 60)
        embedded_manga("Relative", 30)
        embedded_manga("Far", -60)
        body = {
            "liked_ids": [str(seed.id)],
            "disliked_ids": [str(disliked.id)],
            "strategy": "content",
        }

        default = _post(client, **body).json()
        loose = _post(client, **body, dislike_similarity_cutoff=0.8).json()

        assert _titles(default) == ["Relative", "Far"]
        assert _titles(loose) == ["Far"]

    def test_asks_each_source_for_the_requested_candidates(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        for degrees in (5, 10, 15):
            embedded_manga(f"Match {degrees}", degrees)

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            strategy="content",
            candidates_per_source=1,
        ).json()

        assert _titles(payload) == ["Match 5"]

    def test_keeps_only_the_manga_that_carry_every_included_tag(
        self,
        client: TestClient,
        embedded_manga: Callable[[str, float], Manga],
        tag_manga: Callable[[uuid.UUID, str], None],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        both = embedded_manga("Both", 5)
        one = embedded_manga("One", 10)
        for manga, names in ((both, ("action", "drama")), (one, ("action",))):
            for name in names:
                tag_manga(manga.id, name)

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            include_tags=["action", "drama"],
            strategy="content",
        ).json()

        assert _titles(payload) == ["Both"]

    def test_keeps_only_the_requested_types(
        self,
        client: TestClient,
        db_session: Session,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Manga", 5).type = MangaType.MANGA
        embedded_manga("Manhwa", 10).type = MangaType.MANHWA
        db_session.flush()

        payload = _post(
            client, liked_ids=[str(seed.id)], types=["manhwa"], strategy="content"
        ).json()

        assert _titles(payload) == ["Manhwa"]

    def test_keeps_only_the_requested_published_range(
        self,
        client: TestClient,
        db_session: Session,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Old", 5).published_date = date(1995, 1, 1)
        embedded_manga("Recent", 10).published_date = date(2021, 6, 1)
        embedded_manga("Undated", 15)
        db_session.flush()

        payload = _post(
            client,
            liked_ids=[str(seed.id)],
            published_from="2020-01-01",
            strategy="content",
        ).json()

        assert _titles(payload) == ["Recent"]

    def test_keeps_only_the_manga_with_enough_votes(
        self,
        client: TestClient,
        db_session: Session,
        embedded_manga: Callable[[str, float], Manga],
    ) -> None:
        seed = embedded_manga("Seed", 0)
        embedded_manga("Unrated", 5)
        for title, degrees, votes in (("Obscure", 10, 12), ("Popular", 15, 5000)):
            create_manga_metric(
                db_session,
                manga_id=embedded_manga(title, degrees).id,
                bayesian_score=0.7,
                mean_score=0.7,
                votes_count=votes,
                source_count=1,
                computed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        db_session.flush()

        payload = _post(
            client, liked_ids=[str(seed.id)], min_votes=1000, strategy="content"
        ).json()

        assert _titles(payload) == ["Popular"]


class TestRecommendMangaRejects:
    def test_an_empty_liked_ids_list(self, client: TestClient) -> None:
        assert _post(client, liked_ids=[]).status_code == 422

    def test_a_limit_above_the_maximum(self, client: TestClient) -> None:
        response = _post(client, liked_ids=[str(uuid.uuid4())], limit=100_000)

        assert response.status_code == 422

    def test_a_negative_weight(self, client: TestClient) -> None:
        response = _post(
            client, liked_ids=[str(uuid.uuid4())], weights={"content": -5.0}
        )

        assert response.status_code == 422

    def test_a_weight_that_names_no_candidate_source(self, client: TestClient) -> None:
        response = _post(client, liked_ids=[str(uuid.uuid4())], weights={"conten": 1.0})

        assert response.status_code == 422
        assert "conten" in response.json()["detail"][0]["msg"]

    def test_a_rank_constant_of_zero(self, client: TestClient) -> None:
        """The top candidate has rank 0, so a constant of 0 divides by zero."""
        response = _post(client, liked_ids=[str(uuid.uuid4())], rank_constant=0)

        assert response.status_code == 422

    def test_a_dislike_cutoff_above_one(self, client: TestClient) -> None:
        response = _post(
            client, liked_ids=[str(uuid.uuid4())], dislike_similarity_cutoff=1.5
        )

        assert response.status_code == 422

    def test_an_empty_published_range(self, client: TestClient) -> None:
        """`published_to` is exclusive, so equal dates match nothing."""
        response = _post(
            client,
            liked_ids=[str(uuid.uuid4())],
            published_from="2020-01-01",
            published_to="2020-01-01",
        )

        assert response.status_code == 422

    def test_a_min_score_above_one(self, client: TestClient) -> None:
        """`bayesian_score` is a fraction from 0 to 1."""
        response = _post(client, liked_ids=[str(uuid.uuid4())], min_score=8.5)

        assert response.status_code == 422

    def test_more_than_ten_included_tags(self, client: TestClient) -> None:
        tags = [f"tag {index}" for index in range(11)]
        response = _post(client, liked_ids=[str(uuid.uuid4())], include_tags=tags)

        assert response.status_code == 422
