"""Tests for the recommender runner and registry."""

import uuid

import pytest
from sqlalchemy.orm import Session

from manga_recommender.recommender import registry
from manga_recommender.recommender.base import (
    BaseCandidateSource,
    Candidate,
    Reason,
    RecommendationQuery,
)
from manga_recommender.recommender.registry import get_candidate_source
from manga_recommender.recommender.runner import run_recommender
from tests.recommender.queries import make_query


class _FakeSource(BaseCandidateSource):
    """Nominate a fixed list of manga ids, best first."""

    def __init__(self, name: str, manga_ids: list[uuid.UUID]) -> None:
        self.name = name
        self.manga_ids = manga_ids
        self.seen_k: int | None = None

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        self.seen_k = k
        return [
            Candidate(manga_id=manga_id, reasons=[Reason(source=self.name)])
            for manga_id in self.manga_ids
        ]


@pytest.fixture
def no_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the runner with no filters, so only the merge is under test."""
    monkeypatch.setattr(registry, "_FILTERS", [])


def test_get_candidate_source_rejects_an_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown_source"):
        get_candidate_source("unknown_source")


def test_run_recommender_runs_only_the_named_sources(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    no_filters: None,
) -> None:
    wanted_id, skipped_id = uuid.uuid4(), uuid.uuid4()
    skipped = _FakeSource("skipped", [skipped_id])
    monkeypatch.setattr(
        registry,
        "_SOURCE_MAP",
        {"wanted": _FakeSource("wanted", [wanted_id]), "skipped": skipped},
    )

    candidates = run_recommender(db_session, make_query(source_weights={"wanted": 1.0}))

    assert [c.manga_id for c in candidates] == [wanted_id]
    assert skipped.seen_k is None


def test_run_recommender_merges_a_manga_that_two_sources_nominate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    no_filters: None,
) -> None:
    shared_id, only_first_id = uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(
        registry,
        "_SOURCE_MAP",
        {
            "first": _FakeSource("first", [only_first_id, shared_id]),
            "second": _FakeSource("second", [shared_id]),
        },
    )

    candidates = run_recommender(
        db_session, make_query(source_weights={"first": 1.0, "second": 0.5})
    )

    shared = next(c for c in candidates if c.manga_id == shared_id)
    assert len(candidates) == 2
    assert shared.source_ranks == {"first": 1, "second": 0}
    assert {reason.source for reason in shared.reasons} == {"first", "second"}


def test_run_recommender_asks_each_source_for_candidates_per_source(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    no_filters: None,
) -> None:
    source = _FakeSource("content", [uuid.uuid4()])
    monkeypatch.setattr(registry, "_SOURCE_MAP", {"content": source})

    run_recommender(db_session, make_query(candidates_per_source=37, limit=100))

    assert source.seen_k == 37


def test_run_recommender_applies_the_filters_in_registry_order(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _record(name: str, drop: bool) -> object:
        def _filter(
            db: Session,
            query: RecommendationQuery,
            candidates: list[Candidate],
        ) -> list[Candidate]:
            calls.append(name)
            return [] if drop else candidates

        return _filter

    monkeypatch.setattr(
        registry,
        "_SOURCE_MAP",
        {"content": _FakeSource("content", [uuid.uuid4()])},
    )
    monkeypatch.setattr(
        registry, "_FILTERS", [_record("first", False), _record("second", True)]
    )

    candidates = run_recommender(db_session, make_query())

    assert calls == ["first", "second"]
    assert candidates == []
