import pytest
from typer.testing import CliRunner

from manga_recommender import cli

runner = CliRunner()


def test_ingest_with_single_source_calls_run_ingestion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        cli, "run_ingestion", lambda sources, batch_size: calls.append(sources)
    )

    result = runner.invoke(cli.app, ["ingest", "--source", "anilist"])

    assert result.exit_code == 0
    assert calls == [["anilist"]]


def test_ingest_with_repeated_source_collects_all_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        cli, "run_ingestion", lambda sources, batch_size: calls.append(sources)
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
        cli, "run_ingestion", lambda sources, batch_size: calls.append(sources)
    )
    monkeypatch.setattr(
        cli, "get_all_registered_sources", lambda: ["anilist", "mangadex"]
    )

    result = runner.invoke(cli.app, ["ingest", "--all"])

    assert result.exit_code == 0
    assert calls == [["anilist", "mangadex"]]


def test_ingest_without_source_or_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli, "run_ingestion", lambda sources: pytest.fail("should not run")
    )

    result = runner.invoke(cli.app, ["ingest"])

    assert result.exit_code != 0


def test_ingest_with_both_source_and_all_fails_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli, "run_ingestion", lambda sources: pytest.fail("should not run")
    )

    result = runner.invoke(cli.app, ["ingest", "--source", "anilist", "--all"])

    assert result.exit_code != 0
