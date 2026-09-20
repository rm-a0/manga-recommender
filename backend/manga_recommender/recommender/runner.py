import uuid

from sqlalchemy.orm import Session

from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.registry import get_candidate_source, get_filters

_LIMIT_CONSTANT = 5


def run_recommender(db: Session, query: RecommendationQuery) -> None:  # list[Candidate]
    candidates_dict: dict[uuid.UUID, Candidate] = {}

    for source_name in query.source_weights:
        source = get_candidate_source(source_name)
        candidates = source.get_candidates(
            db=db, query=query, k=query.limit * _LIMIT_CONSTANT
        )
        for rank, candidate in enumerate(candidates):
            if candidate.manga_id not in candidates_dict:
                candidates_dict[candidate.manga_id] = candidate
            else:
                candidates_dict[candidate.manga_id].reasons.extend(candidate.reasons)

            candidates_dict[candidate.manga_id].source_ranks[source_name] = rank

    candidates = list(candidates_dict.values())
    for candidate_filter in get_filters():
        candidates = candidate_filter(db, query, candidates)
