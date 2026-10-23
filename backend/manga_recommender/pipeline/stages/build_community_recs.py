"""Turn the community recs artifact into scored neighbours in `manga_similarities`."""

import time
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.orm import Session

from manga_recommender.core import storage
from manga_recommender.core.config import get_pipeline_settings, get_storage_settings
from manga_recommender.db.models.manga_similarities import SimilarityMethod
from manga_recommender.db.repositories.manga_external_rating import (
    get_manga_ids_by_external_id,
)
from manga_recommender.db.repositories.manga_similarities import (
    SimilarityValues,
    bulk_create_manga_similarities,
    delete_manga_similarities_by_method,
)
from manga_recommender.db.repositories.sources import get_source_id_by_name
from manga_recommender.db.session import session_scope

logger = structlog.get_logger(__name__)

# The catalog ingest stores AniList IDs under this source name.
_ANILIST_SOURCE = "anilist"

type _Pair = tuple[uuid.UUID, uuid.UUID]


def _get_anilist_manga_ids(db: Session) -> dict[int, uuid.UUID]:
    """Return the manga ID for each AniList ID in the catalogue.

    Raises `ValueError` when the AniList source does not exist.
    """
    source_id = get_source_id_by_name(db, _ANILIST_SOURCE)
    if source_id is None:
        raise ValueError(
            f"Source '{_ANILIST_SOURCE}' doesn't exist, ingest the catalog first"
        )
    # The artifact holds AniList IDs as integers. The catalogue stores them as text.
    return {
        int(external_id): manga_id
        for external_id, manga_id in get_manga_ids_by_external_id(db, source_id).items()
    }


def _sum_votes(
    rows: Iterable[dict[str, Any]],
    manga_ids: dict[int, uuid.UUID],
) -> dict[_Pair, int]:
    """Return the net votes for each (manga, similar manga) pair.

    Skips edges without positive votes, self-edges, and edges with an end
    outside the catalogue. That last rule also drops deleted and anime targets.
    Several AniList entries can map to one manga, so their votes for the same
    pair add up.
    """
    votes: defaultdict[_Pair, int] = defaultdict(int)
    for row in rows:
        if row["rating"] <= 0:
            continue
        manga_id = manga_ids.get(row["media_id"])
        similar_manga_id = manga_ids.get(row["recommended_id"])
        if manga_id is None or similar_manga_id is None:
            continue
        if manga_id == similar_manga_id:
            continue
        votes[(manga_id, similar_manga_id)] += row["rating"]
    return dict(votes)


def _score_by_vote_share(votes: dict[_Pair, int]) -> list[SimilarityValues]:
    """Score each pair by its share of the votes of its source manga.

    The scores of one manga add up to 1. A popular seed then does not outweigh
    a niche seed when the recommender sums scores over several seeds.
    """
    totals: defaultdict[uuid.UUID, int] = defaultdict(int)
    for (manga_id, _), count in votes.items():
        totals[manga_id] += count
    return [
        SimilarityValues(
            manga_id=manga_id,
            method=SimilarityMethod.COMMUNITY_RECS,
            similar_manga_id=similar_manga_id,
            score=count / totals[manga_id],
        )
        for (manga_id, similar_manga_id), count in votes.items()
    ]


def parse_community_recs(db: Session, path: Path) -> list[SimilarityValues]:
    """Read the artifact at `path` and return one scored row per manga pair.

    Raises `ValueError` when the file is missing or holds no edge between two
    catalogue manga, so the caller never clears the table for an artifact it
    cannot replace it with.
    """
    if not path.exists():
        raise ValueError(f"{path} doesn't exist, no community recs found")

    rows = storage.read_table(path).to_pylist()
    logger.info("artifact_loaded", path=str(path), count=len(rows))

    votes = _sum_votes(rows, _get_anilist_manga_ids(db))
    if not votes:
        raise ValueError(
            f"{path} holds no edges between catalogue manga, refusing to clear the table"
        )

    similarities = _score_by_vote_share(votes)
    logger.info("community_recs_parsed", count=len(similarities))
    return similarities


def replace_community_recs(
    db: Session,
    similarities: Sequence[SimilarityValues],
    batch_size: int,
) -> None:
    """Replace every community recs edge with a recomputed set.

    Deletes the old edges, then inserts the new ones in batches. Edges from
    other methods stay. Every step shares one transaction, so a reader never
    sees the edges missing.
    """
    deleted_count = delete_manga_similarities_by_method(
        db, SimilarityMethod.COMMUNITY_RECS
    )
    logger.info("similarities_deleted", count=deleted_count)
    similarities_count = len(similarities)
    for i in range(0, similarities_count, batch_size):
        batch = similarities[i : i + batch_size]
        start_time = time.monotonic()
        bulk_create_manga_similarities(db, batch)
        logger.info(
            "batch_created",
            count=len(batch),
            elapsed_s=round(time.monotonic() - start_time, 1),
        )
    logger.info("similarities_created", count=similarities_count)


def run_build_community_recs() -> None:
    """Rebuild the community recs edges from the artifact in one transaction."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        replace_community_recs(
            session,
            parse_community_recs(session, get_storage_settings().community_recs_path),
            settings.db_batch_size,
        )
