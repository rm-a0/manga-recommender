from collections.abc import Callable

import pytest

from manga_recommender.pipeline import registry
from manga_recommender.pipeline.registry import (
    get_all_pipeline_stages,
    get_ordered_stages,
    get_stage_callable,
)


def _noop() -> None:
    """Stand in for a stage that does nothing."""
    return


@pytest.fixture
def three_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the real stage map with three stages in a known order."""
    stage_map: dict[str, Callable[[], None]] = {
        "compute_metrics": _noop,
        "export_manga": _noop,
        "embed_manga": _noop,
    }
    monkeypatch.setattr(registry, "_STAGE_MAP", stage_map)


def test_get_all_pipeline_stages_returns_them_in_registry_order(
    three_stages: None,
) -> None:
    assert get_all_pipeline_stages() == [
        "compute_metrics",
        "export_manga",
        "embed_manga",
    ]


def test_get_stage_callable_raises_on_an_unknown_stage() -> None:
    with pytest.raises(ValueError, match="Unknown stage: nope"):
        get_stage_callable("nope")


def test_ordered_stages_ignore_the_order_they_were_asked_for(
    three_stages: None,
) -> None:
    ordered = get_ordered_stages(["embed_manga", "compute_metrics", "export_manga"])

    assert [name for name, _ in ordered] == [
        "compute_metrics",
        "export_manga",
        "embed_manga",
    ]


def test_ordered_stages_collapse_a_repeated_name(three_stages: None) -> None:
    ordered = get_ordered_stages(["compute_metrics", "compute_metrics"])

    assert [name for name, _ in ordered] == ["compute_metrics"]


def test_ordered_stages_return_only_the_requested_stages(three_stages: None) -> None:
    ordered = get_ordered_stages(["embed_manga", "compute_metrics"])

    assert [name for name, _ in ordered] == ["compute_metrics", "embed_manga"]


def test_ordered_stages_reject_an_unknown_name_among_valid_ones(
    three_stages: None,
) -> None:
    # The typo must be caught before the caller gets anything to run.
    with pytest.raises(ValueError, match="Unknown stage: typo"):
        get_ordered_stages(["compute_metrics", "typo"])


def test_ordered_stages_pair_each_name_with_its_own_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    stage_map: dict[str, Callable[[], None]] = {
        "compute_metrics": lambda: calls.append("compute_metrics"),
        "export_manga": lambda: calls.append("export_manga"),
    }
    monkeypatch.setattr(registry, "_STAGE_MAP", stage_map)

    for _, stage_callable in get_ordered_stages(["export_manga", "compute_metrics"]):
        stage_callable()

    assert calls == ["compute_metrics", "export_manga"]
