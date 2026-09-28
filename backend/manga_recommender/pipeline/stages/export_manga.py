"""Export the manga rows that qualify for embedding to a Parquet snapshot."""

import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import structlog
from sqlalchemy.orm import Session

from manga_recommender.core.config import get_pipeline_settings, get_storage_settings
from manga_recommender.db.repositories.manga import stream_exportable_manga
from manga_recommender.db.session import session_scope
from manga_recommender.storage.artifacts import atomic_output

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

    Each `write_batch` call starts a new row group, so `batch_size` also sets
    the row-group size.
    """
    logger.info("export_manga_started", path=str(path), batch_size=db_batch_size)
    exported_count = 0
    with atomic_output(path) as tmp_path, pq.ParquetWriter(tmp_path, SCHEMA) as writer:
        for rows in stream_exportable_manga(db, db_batch_size, description_length):
            start_time = time.monotonic()
            record_batch = pa.RecordBatch.from_arrays(
                list(zip(*rows, strict=True)), schema=SCHEMA
            )
            writer.write_batch(record_batch)
            exported_count += len(rows)
            logger.info(
                "batch_exported",
                count=len(rows),
                elapsed_s=round(time.monotonic() - start_time, 1),
            )
    logger.info("export_manga_completed", path=str(path), count=exported_count)


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
