"""Run pipeline stages in order and stop at the first failure."""

import structlog

from manga_recommender.pipeline.registry import get_ordered_stages

logger = structlog.get_logger(__name__)


def run_pipeline(stages: list[str]) -> None:
    """Run the given stages in registry order and stop at the first failure."""
    ordered_stages = get_ordered_stages(stages)
    for stage_name, stage_callable in ordered_stages:
        logger.info("stage_started", stage=stage_name)
        stage_callable()
        logger.info("stage_completed", stage=stage_name)
