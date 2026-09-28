import pytest
from typer.testing import CliRunner

from manga_recommender.cli import main as cli

runner = CliRunner()

# The ingest command imports these inside its body to keep heavy modules off
# the `app` command's import path. Patch them where they are defined, not on
# `cli`, because the import runs on every invocation.
RUN_CATALOG_INGEST = "manga_recommender.ingestion.catalog.runner.run_catalog_ingest"
REGISTERED_SOURCES = (
    "manga_recommender.ingestion.catalog.registry.get_all_registered_sources"
)
RUN_PIPELINE = "manga_recommender.pipeline.runner.run_pipeline"
RUN_COMMUNITY_RECS = (
    "manga_recommender.ingestion.community_recs.runner.run_community_recs_ingest"
)
PIPELINE_STAGES = "manga_recommender.pipeline.registry.get_all_pipeline_stages"


def test_ingest_catalog_with_single_source_calls_run_catalog_ingest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_CATALOG_INGEST, lambda sources, batch_size: calls.append(sources)
    )

    result = runner.invoke(cli.app, ["ingest", "catalog", "--source", "anilist"])

    assert result.exit_code == 0
    assert calls == [["anilist"]]


def test_ingest_catalog_with_repeated_source_collects_all_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_CATALOG_INGEST, lambda sources, batch_size: calls.append(sources)
    )

    result = runner.invoke(
        cli.app, ["ingest", "catalog", "--source", "anilist", "--source", "mangadex"]
    )

    assert result.exit_code == 0
    assert calls == [["anilist", "mangadex"]]


def test_ingest_catalog_with_all_resolves_registered_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_CATALOG_INGEST, lambda sources, batch_size: calls.append(sources)
    )
    monkeypatch.setattr(REGISTERED_SOURCES, lambda: ["anilist", "mangadex"])

    result = runner.invoke(cli.app, ["ingest", "catalog", "--all"])

    assert result.exit_code == 0
    assert calls == [["anilist", "mangadex"]]


def test_ingest_catalog_without_source_or_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        RUN_CATALOG_INGEST,
        lambda sources, batch_size: pytest.fail("should not run"),
    )

    result = runner.invoke(cli.app, ["ingest", "catalog"])

    assert result.exit_code != 0


def test_ingest_catalog_with_both_source_and_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        RUN_CATALOG_INGEST,
        lambda sources, batch_size: pytest.fail("should not run"),
    )

    result = runner.invoke(
        cli.app, ["ingest", "catalog", "--source", "anilist", "--all"]
    )

    assert result.exit_code != 0


def test_pipeline_with_single_stage_calls_run_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(RUN_PIPELINE, calls.append)

    result = runner.invoke(cli.app, ["pipeline", "--stage", "compute_metrics"])

    assert result.exit_code == 0
    assert calls == [["compute_metrics"]]


def test_pipeline_with_repeated_stage_collects_all_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(RUN_PIPELINE, calls.append)

    result = runner.invoke(
        cli.app, ["pipeline", "--stage", "compute_metrics", "--stage", "export_manga"]
    )

    assert result.exit_code == 0
    assert calls == [["compute_metrics", "export_manga"]]


def test_pipeline_with_all_resolves_registered_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(RUN_PIPELINE, calls.append)
    monkeypatch.setattr(PIPELINE_STAGES, lambda: ["compute_metrics", "export_manga"])

    result = runner.invoke(cli.app, ["pipeline", "--all"])

    assert result.exit_code == 0
    assert calls == [["compute_metrics", "export_manga"]]


def test_pipeline_without_stage_or_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(RUN_PIPELINE, lambda stages: pytest.fail("should not run"))

    result = runner.invoke(cli.app, ["pipeline"])

    assert result.exit_code != 0


def test_pipeline_with_both_stage_and_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(RUN_PIPELINE, lambda stages: pytest.fail("should not run"))

    result = runner.invoke(cli.app, ["pipeline", "--stage", "compute_metrics", "--all"])

    assert result.exit_code != 0


def test_ingest_community_recs_runs_the_crawl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    async def fake_ingest() -> None:
        calls.append(True)

    monkeypatch.setattr(RUN_COMMUNITY_RECS, fake_ingest)

    result = runner.invoke(cli.app, ["ingest", "community-recs"])

    assert result.exit_code == 0, result.output
    assert calls == [True]
