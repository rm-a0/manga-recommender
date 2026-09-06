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
        "fill": _noop,
        "export": _noop,
        "embed": _noop,
    }
    monkeypatch.setattr(registry, "_STAGE_MAP", stage_map)


def test_get_all_pipeline_stages_returns_them_in_registry_order(
    three_stages: None,
) -> None:
    assert get_all_pipeline_stages() == ["fill", "export", "embed"]


def test_get_stage_callable_raises_on_an_unknown_stage() -> None:
    with pytest.raises(ValueError, match="Unknown stage: nope"):
        get_stage_callable("nope")


def test_ordered_stages_ignore_the_order_they_were_asked_for(
    three_stages: None,
) -> None:
    ordered = get_ordered_stages(["embed", "fill", "export"])

    assert [name for name, _ in ordered] == ["fill", "export", "embed"]


def test_ordered_stages_collapse_a_repeated_name(three_stages: None) -> None:
    ordered = get_ordered_stages(["fill", "fill"])

    assert [name for name, _ in ordered] == ["fill"]


def test_ordered_stages_return_only_the_requested_stages(three_stages: None) -> None:
    ordered = get_ordered_stages(["embed", "fill"])

    assert [name for name, _ in ordered] == ["fill", "embed"]


def test_ordered_stages_reject_an_unknown_name_among_valid_ones(
    three_stages: None,
) -> None:
    # The typo must be caught before the caller gets anything to run.
    with pytest.raises(ValueError, match="Unknown stage: typo"):
        get_ordered_stages(["fill", "typo"])


def test_ordered_stages_pair_each_name_with_its_own_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    stage_map: dict[str, Callable[[], None]] = {
        "fill": lambda: calls.append("fill"),
        "export": lambda: calls.append("export"),
    }
    monkeypatch.setattr(registry, "_STAGE_MAP", stage_map)

    for _, stage_callable in get_ordered_stages(["export", "fill"]):
        stage_callable()

    assert calls == ["fill", "export"]
