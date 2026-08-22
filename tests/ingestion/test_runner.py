import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.sources import get_source_by_name
from manga_recommender.ingestion import runner
from manga_recommender.ingestion.base import NormalizedMangaRecord


@pytest.fixture
def patched_session_scope(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> Generator[Session, None, None]:
    """Point `runner.session_scope` at the rolled-back test session.

    `seed_source` opens its own `session_scope()` against the real engine, which
    would otherwise bypass the `db_session` fixture's rollback.
    """

    @contextmanager
    def _fake_scope() -> Iterator[Session]:
        yield db_session
        db_session.flush()

    monkeypatch.setattr(runner, "session_scope", _fake_scope)
    yield db_session


def _record(external_id: str) -> NormalizedMangaRecord:
    return NormalizedMangaRecord(
        external_id=external_id,
        mal_id=None,
        title="Test Manga",
        author="Test Author",
        status=None,
        description=None,
        genres=None,
        published_date=None,
        raw_score=None,
        raw_scale_max=None,
        votes_count=None,
        score_distribution=None,
        fetched_at=datetime.now(UTC),
    )


class _FakeExtractor:
    def __init__(self, records: list[NormalizedMangaRecord]) -> None:
        self._records = records

    def extract(self) -> Iterator[NormalizedMangaRecord]:
        yield from self._records


def test_seed_source_creates_source_with_registered_weight(
    patched_session_scope: Session,
) -> None:
    source_id = runner.seed_source("anilist")

    source = get_source_by_name(patched_session_scope, "anilist")
    assert source is not None
    assert source.id == source_id
    assert source.weight == 1.0


def test_seed_source_is_idempotent(patched_session_scope: Session) -> None:
    first_id = runner.seed_source("anilist")
    second_id = runner.seed_source("anilist")

    assert first_id == second_id


def test_run_ingestion_seeds_source_and_batches_extracted_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = uuid.uuid4()
    seeded: list[str] = []
    loaded_batches: list[tuple[list[NormalizedMangaRecord], uuid.UUID]] = []

    monkeypatch.setattr(
        runner, "seed_source", lambda name: seeded.append(name) or source_id
    )
    monkeypatch.setattr(
        runner,
        "get_extractor_for_source",
        lambda name: _FakeExtractor([_record("1"), _record("2"), _record("3")]),
    )
    monkeypatch.setattr(
        runner,
        "load_batch",
        lambda records, sid, genre_cache: loaded_batches.append((records, sid)),
    )

    runner.run_ingestion(["anilist"], batch_size=2)

    assert seeded == ["anilist"]
    assert [sid for _, sid in loaded_batches] == [source_id, source_id]
    assert [len(batch) for batch, _ in loaded_batches] == [2, 1]


def test_run_ingestion_continues_after_a_source_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed: list[str] = []

    def _seed_source(name: str) -> uuid.UUID:
        if name == "broken":
            raise ValueError("boom")
        processed.append(name)
        return uuid.uuid4()

    monkeypatch.setattr(runner, "seed_source", _seed_source)
    monkeypatch.setattr(
        runner, "get_extractor_for_source", lambda name: _FakeExtractor([])
    )
    monkeypatch.setattr(runner, "load_batch", lambda records, sid, genre_cache: None)

    runner.run_ingestion(["broken", "anilist"], batch_size=50)

    assert processed == ["anilist"]
