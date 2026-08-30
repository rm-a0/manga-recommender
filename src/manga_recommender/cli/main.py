"""Typer CLI: run ingestion or start the API server."""

from typing import Annotated

import typer
import uvicorn

from manga_recommender.core.config import (
    get_api_settings,
    get_app_settings,
    get_ingestion_settings,
    get_logging_settings,
)
from manga_recommender.core.logging_config import configure_logging
from manga_recommender.ingestion.registry import get_all_registered_sources
from manga_recommender.ingestion.runner import run_ingestion

app = typer.Typer(help="CLI for the manga recommender.")


@app.callback()
def main() -> None:
    """Configure logging before any Typer command runs."""
    configure_logging(
        level=get_logging_settings().level,
        debug=get_app_settings().debug,
    )


@app.command(name="ingest")
def ingest(
    source: Annotated[
        list[str] | None,
        typer.Option("--source", help="Source to ingest (repeatable)."),
    ] = None,
    all_sources: Annotated[
        bool,
        typer.Option("--all", help="Ingest every registered source."),
    ] = False,
) -> None:
    """Run the ingestion pipeline. Pick either --source or --all."""
    if (source and all_sources) or (not source and not all_sources):
        raise typer.BadParameter("Pass either --source (one or more) or --all.")
    sources = get_all_registered_sources() if all_sources else source
    if sources is None:
        raise RuntimeError("No sources to ingest.")
    run_ingestion(sources, batch_size=get_ingestion_settings().batch_size)


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


if __name__ == "__main__":
    app()
