"""Export the manga rows that qualify for embedding to a Parquet snapshot."""

import time
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

import pyarrow as pa
import structlog
from sqlalchemy import Row
from sqlalchemy.orm import Session

from manga_recommender.core import storage
from manga_recommender.core.config import get_pipeline_settings, get_storage_settings
from manga_recommender.db.repositories.manga import stream_exportable_manga
from manga_recommender.db.session import session_scope

logger = structlog.get_logger(__name__)

SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("title", pa.string()),
        ("description", pa.string()),
        ("tags", pa.list_(pa.string())),
    ]
)


def create_manga_parquet(
    db: Session,
    path: Path,
    db_batch_size: int,
    description_length: int,
) -> None:
    """Write the export snapshot to `path`, one row group per streamed batch.

    `db_batch_size` also sets the row-group size.
    """
    logger.info("export_manga_started", path=str(path), batch_size=db_batch_size)
    rows = stream_exportable_manga(db, db_batch_size, description_length)
    count = storage.write_batches(path, SCHEMA, _to_record_batches(rows))
    logger.info("export_manga_completed", path=str(path), count=count)


def _to_record_batches(
    row_batches: Iterable[Sequence[Row]],
) -> Iterator[pa.RecordBatch]:
    for rows in row_batches:
        start_time = time.monotonic()
        yield pa.RecordBatch.from_arrays(list(zip(*rows, strict=True)), schema=SCHEMA)
        logger.info(
            "batch_exported",
            count=len(rows),
            elapsed_s=round(time.monotonic() - start_time, 1),
        )


def run_export_manga() -> None:
    """Read the qualifying manga and write the Parquet snapshot."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        create_manga_parquet(
            session,
            get_storage_settings().manga_snapshot_path,
            settings.db_batch_size,
            settings.min_description_length,
        )
