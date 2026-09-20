"""Helpers that the candidate sources share. These are not sources themselves."""

import uuid
from collections.abc import Collection, Sequence
from typing import NamedTuple

from manga_recommender.recommender.base import Candidate, Reason


class SeedMatches(NamedTuple):
    """Hold one liked manga and the ids of the manga that match it, best first.

    Each source decides what a match is. The content source measures the
    distance between two vectors. The tags source counts shared tags.
    """

    seed_id: uuid.UUID
    match_ids: Sequence[uuid.UUID]


def round_robin_merge(
    matches_per_seed: Sequence[SeedMatches],
    skip_ids: Collection[uuid.UUID],
    source_name: str,
    k: int,
) -> list[Candidate]:
    """Merge the match lists of all seeds into up to `k` candidates.

    Take one match from each seed per rank, so that each seed gets its
    best matches near the top. A match of more than one seed gets one
    reason for each seed.
    """
    candidates: dict[uuid.UUID, Candidate] = {}

    for rank in range(k):
        if len(candidates) >= k:
            break

        for seed_id, match_ids in matches_per_seed:
            if rank >= len(match_ids):
                continue

            match_id = match_ids[rank]
            if match_id in skip_ids:
                continue
            elif match_id in candidates:
                candidates[match_id].reasons.append(
                    Reason(source=source_name, seed_id=seed_id)
                )
            else:
                candidates[match_id] = Candidate(
                    manga_id=match_id,
                    reasons=[Reason(source=source_name, seed_id=seed_id)],
                )

    return [*candidates.values()][:k]
