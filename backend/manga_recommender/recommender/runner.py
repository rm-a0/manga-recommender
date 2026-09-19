import uuid

from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.registry import get_candidate_source
from sqlalchemy.orm import Session

_LIMIT_CONSTANT = 5


def run_recommender(db: Session, query: RecommendationQuery) -> None:
    candidates_dict: dict[uuid.UUID, Candidate] = {}

    for source_weight, source_name in query.source_weights:
        source = get_candidate_source(source_name)
        candidates = source.get_candidates(
            db=db, query=query, k=query.limit * _LIMIT_CONSTANT
        )
        for rank, candidate in enumerate(candidates):
            if not candidates_dict[candidate.manga_id]:
                candidates_dict[candidate.manga_id] = candidate
            else:
                candidates_dict[candidate.manga_id].reasons.extend(candidate.reasons)

            candidates_dict[candidate.manga_id].source_ranks[source_name] = rank
