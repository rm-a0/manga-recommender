import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from sqlalchemy import Row
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    bulk_add_tags_to_manga,
    create_manga,
)
from manga_recommender.db.repositories.tags import get_or_create_tag
from manga_recommender.pipeline.stages import export
from manga_recommender.pipeline.stages.export import SCHEMA, create_manga_parquet

MINIMUM_LENGTH = 100
QUALIFYING_DESCRIPTION = "x" * 150


def _seed(
    db: Session,
    title: str,
    *,
    description: str | None,
    title_english: str | None = None,
) -> uuid.UUID:
    """Create one manga and return its ID."""
    return create_manga(
        db, title=title, title_english=title_english, description=description
    ).id


def _link_tag(db: Session, manga_id: uuid.UUID, name: str, *, rank: int | None) -> None:
    """Attach one ranked tag to a manga."""
    tag = get_or_create_tag(db, name=name, category=None, is_explicit=False)
    bulk_add_tags_to_manga(
        db,
        [TagLinkValues(manga_id=manga_id, tag_id=tag.id, rank=rank, is_spoiler=False)],
    )


def _read(path: Path) -> list[dict[str, object]]:
    """Return the snapshot's rows, ordered by title."""
    rows = pq.read_table(path).to_pylist()
    return sorted(rows, key=lambda row: str(row["title"]))


def test_create_manga_parquet_writes_the_declared_schema(
    db_session: Session, tmp_path: Path
) -> None:
    _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    assert pq.read_table(path).schema == SCHEMA


def test_create_manga_parquet_writes_only_the_qualifying_rows(
    db_session: Session, tmp_path: Path
) -> None:
    _seed(db_session, "Long enough", description=QUALIFYING_DESCRIPTION)
    _seed(db_session, "Too short", description="x" * 99)
    _seed(db_session, "No description", description=None)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    assert [row["title"] for row in _read(path)] == ["Long enough"]


def test_create_manga_parquet_carries_the_row_fields_through(
    db_session: Session, tmp_path: Path
) -> None:
    manga_id = _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    _link_tag(db_session, manga_id, "Action", rank=3)
    _link_tag(db_session, manga_id, "Drama", rank=9)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    (row,) = _read(path)
    assert row["id"] == str(manga_id)
    assert row["title"] == "Berserk"
    assert row["description"] == QUALIFYING_DESCRIPTION
    assert row["tags"] == ["Drama", "Action"]


def test_create_manga_parquet_prefers_the_english_title(
    db_session: Session, tmp_path: Path
) -> None:
    """The snapshot carries the title a reader sees, so English wins when stored."""
    _seed(
        db_session,
        "Shingeki no Kyojin",
        title_english="Attack on Titan",
        description=QUALIFYING_DESCRIPTION,
    )
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    (row,) = _read(path)
    assert row["title"] == "Attack on Titan"


def test_create_manga_parquet_falls_back_to_the_romaji_title(
    db_session: Session, tmp_path: Path
) -> None:
    _seed(db_session, "Berserk", title_english=None, description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    (row,) = _read(path)
    assert row["title"] == "Berserk"


def test_create_manga_parquet_writes_no_tags_as_null(
    db_session: Session, tmp_path: Path
) -> None:
    # The subquery aggregates zero rows to NULL. Nothing downstream may assume
    # every row carries a list.
    _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    (row,) = _read(path)
    assert row["tags"] is None


def test_create_manga_parquet_starts_a_row_group_for_each_batch(
    db_session: Session, tmp_path: Path
) -> None:
    # Each write_batch call opens a new row group, so the batch size sets the
    # row-group size as well as the database round trip.
    for i in range(5):
        _seed(db_session, f"Manga {i}", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 2, MINIMUM_LENGTH)

    assert pq.ParquetFile(path).num_row_groups == 3


def test_create_manga_parquet_creates_the_parent_directory(
    db_session: Session, tmp_path: Path
) -> None:
    _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "artifacts" / "nested" / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    assert path.exists()


def test_create_manga_parquet_writes_an_empty_snapshot_when_nothing_qualifies(
    db_session: Session, tmp_path: Path
) -> None:
    # No batch is ever yielded here, so nothing in the loop body runs. The row
    # count and the row-group count still have to be reportable.
    _seed(db_session, "Too short", description="x" * 99)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    table = pq.read_table(path)
    assert table.num_rows == 0
    assert table.schema == SCHEMA


def test_create_manga_parquet_leaves_no_temporary_file(
    db_session: Session, tmp_path: Path
) -> None:
    _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    assert [p.name for p in tmp_path.iterdir()] == ["manga.parquet"]


def test_create_manga_parquet_keeps_the_previous_snapshot_when_the_stream_fails(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A half-written snapshot must never reach the real path: the embed stage
    # cannot tell a truncated file from a complete one.
    _seed(db_session, "Berserk", description=QUALIFYING_DESCRIPTION)
    path = tmp_path / "manga.parquet"
    create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)
    original = path.read_bytes()

    def _failing_stream(
        db: Session, batch_size: int, description_length: int
    ) -> Iterator[Sequence[Row]]:
        yield from ()
        raise RuntimeError("connection lost")

    monkeypatch.setattr(export, "stream_exportable_manga", _failing_stream)

    with pytest.raises(RuntimeError, match="connection lost"):
        create_manga_parquet(db_session, path, 100, MINIMUM_LENGTH)

    assert path.read_bytes() == original
    assert [p.name for p in tmp_path.iterdir()] == ["manga.parquet"]


def test_create_manga_parquet_applies_the_given_minimum_length(
    db_session: Session, tmp_path: Path
) -> None:
    # The stage owns no threshold of its own. It writes whatever the caller's
    # minimum admits.
    _seed(db_session, "Fifty", description="x" * 50)
    path = tmp_path / "manga.parquet"

    create_manga_parquet(db_session, path, 100, 50)

    assert [row["title"] for row in _read(path)] == ["Fifty"]
