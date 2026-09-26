"""Run one recommendation: nominate candidates, then filter, score and select."""

import uuid

from sqlalchemy.orm import Session

from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.registry import (
    get_candidate_source,
    get_filters,
    get_scorers,
    get_selectors,
)


def _run_sources(db: Session, query: RecommendationQuery) -> list[Candidate]:
    """Return the candidates of every named source, merged into one list.

    Run only the sources that `query.source_weights` names. A manga that more
    than one source nominates stays one candidate. It keeps the reasons of each
    source and its rank in each source.
    """
    candidates_by_id: dict[uuid.UUID, Candidate] = {}

    for source_name in query.source_weights:
        source = get_candidate_source(source_name)
        candidates = source.get_candidates(
            db=db,
            query=query,
            k=query.candidates_per_source,
        )

        for rank, candidate in enumerate(candidates):
            merged = candidates_by_id.get(candidate.manga_id)
            if merged is None:
                candidates_by_id[candidate.manga_id] = candidate
                merged = candidate
            else:
                merged.reasons.extend(candidate.reasons)
            merged.source_ranks[source_name] = rank

    return list(candidates_by_id.values())


def _apply_filters(
    db: Session,
    query: RecommendationQuery,
    candidates: list[Candidate],
) -> list[Candidate]:
    """Return the candidates that pass every filter, in registry order."""
    for candidate_filter in get_filters():
        candidates = candidate_filter(db, query, candidates)
    return candidates


def _run_scorers(
    query: RecommendationQuery,
    candidates: list[Candidate],
) -> list[Candidate]:
    """Return the candidates with their scores set, in registry order."""
    for scorer in get_scorers():
        candidates = scorer(query, candidates)
    return candidates


def _run_selectors(
    query: RecommendationQuery,
    candidates: list[Candidate],
) -> list[Candidate]:
    """Return the candidates the reader sees, in display order."""
    for selector in get_selectors():
        candidates = selector(query, candidates)
    return candidates


def run_recommender(db: Session, query: RecommendationQuery) -> list[Candidate]:
    """Return the recommended candidates for one query."""
    candidates = _run_sources(db, query)
    candidates = _apply_filters(db, query, candidates)
    candidates = _run_scorers(query, candidates)
    return _run_selectors(query, candidates)
