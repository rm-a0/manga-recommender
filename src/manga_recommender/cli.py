"""Typer CLI: run ingestion or start the API server."""

from typing import Annotated

import typer

from manga_recommender.ingestion.registry import get_all_registered_sources
from manga_recommender.ingestion.runner import run_ingestion

app = typer.Typer(help="CLI for the manga recommender.")


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
    run_ingestion(sources)


@app.command(name="app")
def start_app() -> None:
    """Start the FastAPI application."""
    print("TODO")


if __name__ == "__main__":
    app()
