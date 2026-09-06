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
            "fill": _record("fill"),
            "export": _record("export"),
            "embed": _record("embed"),
        },
    )
    return calls


def test_run_pipeline_runs_the_stages_in_registry_order(
    recorded_stages: list[str],
) -> None:
    run_pipeline(["embed", "fill", "export"])

    assert recorded_stages == ["fill", "export", "embed"]


def test_run_pipeline_runs_only_the_requested_stages(
    recorded_stages: list[str],
) -> None:
    run_pipeline(["embed"])

    assert recorded_stages == ["embed"]


def test_run_pipeline_stops_at_the_first_failing_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _boom() -> None:
        calls.append("export")
        raise RuntimeError("export blew up")

    monkeypatch.setattr(
        registry,
        "_STAGE_MAP",
        {
            "fill": lambda: calls.append("fill"),
            "export": _boom,
            "embed": lambda: calls.append("embed"),
        },
    )

    with pytest.raises(RuntimeError, match="export blew up"):
        run_pipeline(["fill", "export", "embed"])

    # `embed` must not run. Unlike ingestion, the pipeline halts on failure.
    assert calls == ["fill", "export"]


def test_run_pipeline_runs_nothing_when_one_stage_name_is_unknown(
    recorded_stages: list[str],
) -> None:
    with pytest.raises(ValueError, match="Unknown stage: typo"):
        run_pipeline(["fill", "typo"])

    assert recorded_stages == []


def test_run_pipeline_logs_the_start_and_the_finish_of_every_stage(
    recorded_stages: list[str],
) -> None:
    with structlog.testing.capture_logs() as logs:
        run_pipeline(["fill", "export"])

    assert [(entry["event"], entry["stage"]) for entry in logs] == [
        ("stage_started", "fill"),
        ("stage_completed", "fill"),
        ("stage_started", "export"),
        ("stage_completed", "export"),
    ]
