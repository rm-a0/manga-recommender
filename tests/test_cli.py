import pytest
from typer.testing import CliRunner

from manga_recommender.cli import main as cli

runner = CliRunner()

# The ingest command imports these inside its body to keep heavy modules off
# the `app` command's import path. Patch them where they are defined, not on
# `cli`, because the import runs on every invocation.
RUN_INGESTION = "manga_recommender.ingestion.runner.run_ingestion"
REGISTERED_SOURCES = "manga_recommender.ingestion.registry.get_all_registered_sources"


def test_ingest_with_single_source_calls_run_ingestion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_INGESTION, lambda sources, batch_size: calls.append(sources)
    )

    result = runner.invoke(cli.app, ["ingest", "--source", "anilist"])

    assert result.exit_code == 0
    assert calls == [["anilist"]]


def test_ingest_with_repeated_source_collects_all_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_INGESTION, lambda sources, batch_size: calls.append(sources)
    )

    result = runner.invoke(
        cli.app, ["ingest", "--source", "anilist", "--source", "mangadex"]
    )

    assert result.exit_code == 0
    assert calls == [["anilist", "mangadex"]]


def test_ingest_with_all_resolves_registered_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        RUN_INGESTION, lambda sources, batch_size: calls.append(sources)
    )
    monkeypatch.setattr(REGISTERED_SOURCES, lambda: ["anilist", "mangadex"])

    result = runner.invoke(cli.app, ["ingest", "--all"])

    assert result.exit_code == 0
    assert calls == [["anilist", "mangadex"]]


def test_ingest_without_source_or_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        RUN_INGESTION,
        lambda sources, batch_size: pytest.fail("should not run"),
    )

    result = runner.invoke(cli.app, ["ingest"])

    assert result.exit_code != 0


def test_ingest_with_both_source_and_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        RUN_INGESTION,
        lambda sources, batch_size: pytest.fail("should not run"),
    )

    result = runner.invoke(cli.app, ["ingest", "--source", "anilist", "--all"])

    assert result.exit_code != 0
