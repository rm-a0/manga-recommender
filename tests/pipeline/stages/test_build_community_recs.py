import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.core import storage
from manga_recommender.db.models.manga_similarities import (
    MangaSimilarity,
    SimilarityMethod,
)
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.db.repositories.manga_external_rating import (
    create_external_rating,
)
from manga_recommender.db.repositories.manga_similarities import (
    SimilarityValues,
    bulk_create_manga_similarities,
)
from manga_recommender.ingestion.community_recs.anilist import EDGE_SCHEMA
from manga_recommender.pipeline.stages.build_community_recs import (
    _score_by_vote_share,
    _sum_votes,
    parse_community_recs,
    replace_community_recs,
)

A, B, C = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _row(
    media_id: int,
    recommended_id: int | None,
    rating: int,
    recommended_type: str | None = "MANGA",
) -> dict[str, Any]:
    """Build one artifact row in the shape the community recs ingest writes."""
    return {
        "media_id": media_id,
        "recommended_id": recommended_id,
        "recommended_type": recommended_type,
        "rating": rating,
    }


def _build(db: Session, path: Path, batch_size: int = 100) -> None:
    """Run the stage on `path` the way `run_build_community_recs` does."""
    replace_community_recs(db, parse_community_recs(db, path), batch_size)


def _write_artifact(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write `rows` as a community recs artifact."""
    storage.write_table(path, pa.Table.from_pylist(rows, schema=EDGE_SCHEMA))


def _catalogue(db: Session, anilist_ids: list[int]) -> dict[int, uuid.UUID]:
    """Create one manga per AniList ID under the `anilist` source.

    Return the manga ID for each AniList ID.
    """
    source = Source(name="anilist")
    db.add(source)
    db.flush()
    manga_ids = {}
    for anilist_id in anilist_ids:
        manga = create_manga(db, title=f"AniList {anilist_id}")
        create_external_rating(
            db,
            manga_id=manga.id,
            source_id=source.id,
            external_id=str(anilist_id),
            fetched_at=datetime.now(UTC),
        )
        manga_ids[anilist_id] = manga.id
    return manga_ids


def _stored(
    db: Session, method: SimilarityMethod = SimilarityMethod.COMMUNITY_RECS
) -> dict[tuple[uuid.UUID, uuid.UUID], float]:
    """Reload the score of every edge of `method` straight from the database."""
    db.expire_all()
    rows = db.scalars(select(MangaSimilarity).where(MangaSimilarity.method == method))
    return {(row.manga_id, row.similar_manga_id): row.score for row in rows}


# --- _sum_votes ---


def test_sum_votes_keeps_an_edge_between_catalogue_manga() -> None:
    assert _sum_votes([_row(1, 2, 5)], {1: A, 2: B}) == {(A, B): 5}


def test_sum_votes_skips_edges_without_positive_votes() -> None:
    rows = [_row(1, 2, 0), _row(1, 2, -3)]

    assert _sum_votes(rows, {1: A, 2: B}) == {}


def test_sum_votes_skips_deleted_and_anime_targets() -> None:
    # AniList IDs are unique across anime and manga, so an anime target is never
    # in the catalogue.
    rows = [_row(1, 50, 5, recommended_type="ANIME"), _row(1, None, 5, None)]

    assert _sum_votes(rows, {1: A, 2: B}) == {}


def test_sum_votes_skips_edges_with_an_end_outside_the_catalogue() -> None:
    rows = [_row(1, 99, 5), _row(99, 1, 5)]

    assert _sum_votes(rows, {1: A}) == {}


def test_sum_votes_adds_up_entries_that_share_a_manga() -> None:
    # AniList 1 and 2 are one manga in the catalogue, so their edge to 3 is one
    # pair, and their edge to each other is a self-edge.
    rows = [_row(1, 3, 4), _row(2, 3, 6), _row(1, 2, 7)]

    assert _sum_votes(rows, {1: A, 2: A, 3: B}) == {(A, B): 10}


# --- _score_by_vote_share ---


def test_score_by_vote_share_splits_each_manga_votes_into_shares() -> None:
    scores = _score_by_vote_share({(A, B): 3, (A, C): 1, (B, A): 5})

    assert scores == [
        SimilarityValues(
            manga_id=A,
            method=SimilarityMethod.COMMUNITY_RECS,
            similar_manga_id=B,
            score=0.75,
        ),
        SimilarityValues(
            manga_id=A,
            method=SimilarityMethod.COMMUNITY_RECS,
            similar_manga_id=C,
            score=0.25,
        ),
        SimilarityValues(
            manga_id=B,
            method=SimilarityMethod.COMMUNITY_RECS,
            similar_manga_id=A,
            score=1.0,
        ),
    ]


# --- parse_community_recs + replace_community_recs ---


def test_build_writes_every_scored_edge(db_session: Session, tmp_path: Path) -> None:
    ids = _catalogue(db_session, [1, 2, 3])
    path = tmp_path / "community_recs.parquet"
    _write_artifact(path, [_row(1, 2, 3), _row(1, 3, 1), _row(2, 1, 3)])

    # A batch size below the edge count exercises more than one insert.
    _build(db_session, path, batch_size=2)

    assert _stored(db_session) == {
        (ids[1], ids[2]): 0.75,
        (ids[1], ids[3]): 0.25,
        (ids[2], ids[1]): 1.0,
    }


def test_build_drops_edges_that_left_the_artifact(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _catalogue(db_session, [1, 2, 3])
    path = tmp_path / "community_recs.parquet"
    _write_artifact(path, [_row(1, 2, 3), _row(1, 3, 1)])
    _build(db_session, path)

    _write_artifact(path, [_row(1, 2, 3)])
    _build(db_session, path)

    assert _stored(db_session) == {(ids[1], ids[2]): 1.0}


def test_build_keeps_edges_from_other_methods(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _catalogue(db_session, [1, 2])
    bulk_create_manga_similarities(
        db_session,
        [
            SimilarityValues(
                manga_id=ids[2],
                method=SimilarityMethod.COLLAB,
                similar_manga_id=ids[1],
                score=0.9,
            )
        ],
    )
    path = tmp_path / "community_recs.parquet"
    _write_artifact(path, [_row(1, 2, 3)])

    _build(db_session, path)

    assert _stored(db_session, SimilarityMethod.COLLAB) == {(ids[2], ids[1]): 0.9}


def test_build_rejects_a_missing_artifact(db_session: Session, tmp_path: Path) -> None:
    _catalogue(db_session, [1])

    with pytest.raises(ValueError, match="doesn't exist"):
        _build(db_session, tmp_path / "missing.parquet")


def test_build_rejects_a_catalogue_without_the_anilist_source(
    db_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "community_recs.parquet"
    _write_artifact(path, [_row(1, 2, 3)])

    with pytest.raises(ValueError, match="Source 'anilist' doesn't exist"):
        _build(db_session, path)


def test_build_rejects_an_artifact_without_catalogue_edges_and_keeps_the_table(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _catalogue(db_session, [1, 2])
    path = tmp_path / "community_recs.parquet"
    _write_artifact(path, [_row(1, 2, 3)])
    _build(db_session, path)

    # Neither end of this edge is in the catalogue.
    _write_artifact(path, [_row(98, 99, 3)])

    with pytest.raises(ValueError, match="holds no edges"):
        _build(db_session, path)

    assert _stored(db_session) == {(ids[1], ids[2]): 1.0}
