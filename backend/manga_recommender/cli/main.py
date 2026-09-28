"""Typer CLI: ingest data, run the pipeline, or start the API server.

Commands import ingestion and pipeline code inside their body. Those modules
need the optional `pipeline` and `ml` dependency groups, which `app` does not.
"""

import asyncio
from collections.abc import Callable
from typing import Annotated

import typer
import uvicorn

from manga_recommender.core.config import (
    get_api_settings,
    get_app_settings,
    get_ingestion_settings,
    get_logging_settings,
)

app = typer.Typer(help="CLI for the manga recommender.")
ingest_app = typer.Typer(help="Pull data from external sources.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")


@app.callback()
def main() -> None:
    """Configure logging before any Typer command runs."""
    from manga_recommender.core.logging_config import configure_logging

    configure_logging(
        level=get_logging_settings().level,
        debug=get_app_settings().debug,
    )


@ingest_app.command(name="catalog")
def ingest_catalog(
    source: Annotated[
        list[str] | None,
        typer.Option("--source", help="Source to ingest (repeatable)."),
    ] = None,
    all_sources: Annotated[
        bool,
        typer.Option("--all", help="Ingest every registered source."),
    ] = False,
) -> None:
    """Normalize manga metadata and upsert it into Postgres."""
    from manga_recommender.ingestion.catalog import registry, runner

    sources = _pick(
        source, all_sources, registry.get_all_registered_sources, "--source"
    )
    runner.run_catalog_ingest(
        sources, batch_size=get_ingestion_settings().db_batch_size
    )


@ingest_app.command(name="community-recs")
def ingest_community_recs() -> None:
    """Crawl AniList community recommendations into one Parquet artifact."""
    from manga_recommender.ingestion.community_recs import runner

    asyncio.run(runner.run_community_recs_ingest())


@app.command(name="pipeline")
def start_pipeline(
    stage: Annotated[
        list[str] | None,
        typer.Option("--stage", help="Stage to run (repeatable)."),
    ] = None,
    all_stages: Annotated[
        bool,
        typer.Option("--all", help="Run every stage in the pipeline."),
    ] = False,
) -> None:
    """Run the pipeline stages."""
    from manga_recommender.pipeline import registry, runner

    runner.run_pipeline(
        _pick(stage, all_stages, registry.get_all_pipeline_stages, "--stage")
    )


@app.command(name="app")
def start_app() -> None:
    """Start the FastAPI application with uvicorn."""
    settings = get_api_settings()
    # Pass the import string, not the app object: uvicorn re-imports it per
    # worker process, which `--workers` and `--reload` both need.
    uvicorn.run(
        "manga_recommender.api.main:app",
        host=settings.host,
        port=settings.port,
    )


def _pick(
    chosen: list[str] | None,
    use_all: bool,
    get_all: Callable[[], list[str]],
    option: str,
) -> list[str]:
    """Return the chosen names, or every name for `--all`. Reject both and neither."""
    if use_all and not chosen:
        return get_all()
    if chosen and not use_all:
        return chosen
    raise typer.BadParameter(f"Pass either {option} (one or more) or --all.")


if __name__ == "__main__":
    app()
