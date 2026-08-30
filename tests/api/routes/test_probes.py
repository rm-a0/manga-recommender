from fastapi.testclient import TestClient


class TestHealth:
    def test_reports_ok(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_answers_without_the_database(
        self, client_with_broken_db: TestClient
    ) -> None:
        """Liveness must not depend on Postgres, or a blip restarts the app."""
        response = client_with_broken_db.get("/health")

        assert response.status_code == 200


class TestReadiness:
    def test_reports_ready_when_the_database_answers(self, client: TestClient) -> None:
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready", "checks": {"database": True}}

    def test_reports_503_when_the_database_is_unreachable(
        self, client_with_broken_db: TestClient
    ) -> None:
        response = client_with_broken_db.get("/ready")

        assert response.status_code == 503
        assert response.json() == {"status": "degraded", "checks": {"database": False}}
