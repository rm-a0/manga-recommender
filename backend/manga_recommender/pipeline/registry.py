"""Map a stage name to the function that runs it."""

from collections.abc import Callable, Sequence

from manga_recommender.pipeline.stages.compute_metrics import run_compute_metrics
from manga_recommender.pipeline.stages.embed_manga import run_embed_manga
from manga_recommender.pipeline.stages.export_manga import run_export_manga
from manga_recommender.pipeline.stages.load_embeddings import run_load_embeddings

_STAGE_MAP: dict[str, Callable[[], None]] = {
    "compute_metrics": run_compute_metrics,
    "export_manga": run_export_manga,
    "embed_manga": run_embed_manga,
    "load_embeddings": run_load_embeddings,
}


def get_all_pipeline_stages() -> list[str]:
    """Return every pipeline stage name, in the order the stages must run."""
    return list(_STAGE_MAP.keys())


def get_stage_callable(stage_name: str) -> Callable[[], None]:
    """Return the function that runs the given stage."""
    stage = _STAGE_MAP.get(stage_name)
    if stage is None:
        raise ValueError(f"Unknown stage: {stage_name}")
    return stage


def get_ordered_stages(
    stage_names: list[str],
) -> Sequence[tuple[str, Callable[[], None]]]:
    """Return the given stages as (name, function) pairs, in run order.

    Rejects an unknown name before it returns anything, so a typo cannot let
    the first stages run. Repeated names collapse to one pair.
    """
    for name in stage_names:
        if name not in _STAGE_MAP:
            raise ValueError(f"Unknown stage: {name}")
    return [
        (stage_name, stage_callable)
        for stage_name, stage_callable in _STAGE_MAP.items()
        if stage_name in stage_names
    ]
