from manga_recommender.recommender.base import BaseCandidateSource
from manga_recommender.recommender.candidate_sources.content import (
    ContentCandidateSource,
)

_SOURCE_MAP: dict[str, BaseCandidateSource] = {
    "content": ContentCandidateSource(),
}


def get_candidate_source(name: str) -> BaseCandidateSource:
    source = _SOURCE_MAP.get(name)
    if source is None:
        raise ValueError(f"Unknown candidate source: {source}")
    return source
