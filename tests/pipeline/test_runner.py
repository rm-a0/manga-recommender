from collections.abc import Callable

import pytest
import structlog

from manga_recommender.pipeline import registry
from manga_recommender.pipeline.runner import run_pipeline


@pytest.fixture
def recorded_stages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Register three stages that record their own name when they run."""
    calls: list[str] = []

    def _record(name: str) -> Callable[[], None]:
        return lambda: calls.append(name)

    monkeypatch.setattr(
        registry,
        "_STAGE_MAP",
        {
            "compute_metrics": _record("compute_metrics"),
            "export_manga": _record("export_manga"),
            "embed_manga": _record("embed_manga"),
        },
    )
    return calls


def test_run_pipeline_runs_the_stages_in_registry_order(
    recorded_stages: list[str],
) -> None:
    run_pipeline(["embed_manga", "compute_metrics", "export_manga"])

    assert recorded_stages == ["compute_metrics", "export_manga", "embed_manga"]


def test_run_pipeline_runs_only_the_requested_stages(
    recorded_stages: list[str],
) -> None:
    run_pipeline(["embed_manga"])

    assert recorded_stages == ["embed_manga"]


def test_run_pipeline_stops_at_the_first_failing_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _boom() -> None:
        calls.append("export_manga")
        raise RuntimeError("export blew up")

    monkeypatch.setattr(
        registry,
        "_STAGE_MAP",
        {
            "compute_metrics": lambda: calls.append("compute_metrics"),
            "export_manga": _boom,
            "embed_manga": lambda: calls.append("embed_manga"),
        },
    )

    with pytest.raises(RuntimeError, match="export blew up"):
        run_pipeline(["compute_metrics", "export_manga", "embed_manga"])

    # `embed_manga` must not run. Unlike ingestion, the pipeline halts on failure.
    assert calls == ["compute_metrics", "export_manga"]


def test_run_pipeline_runs_nothing_when_one_stage_name_is_unknown(
    recorded_stages: list[str],
) -> None:
    with pytest.raises(ValueError, match="Unknown stage: typo"):
        run_pipeline(["compute_metrics", "typo"])

    assert recorded_stages == []


def test_run_pipeline_logs_the_start_and_the_finish_of_every_stage(
    recorded_stages: list[str],
) -> None:
    with structlog.testing.capture_logs() as logs:
        run_pipeline(["compute_metrics", "export_manga"])

    assert [(entry["event"], entry["stage"]) for entry in logs] == [
        ("stage_started", "compute_metrics"),
        ("stage_completed", "compute_metrics"),
        ("stage_started", "export_manga"),
        ("stage_completed", "export_manga"),
    ]
