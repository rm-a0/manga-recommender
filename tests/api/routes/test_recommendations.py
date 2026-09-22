"""Tests for the recommendation routes."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from manga_recommender.db.models.manga import Manga


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
