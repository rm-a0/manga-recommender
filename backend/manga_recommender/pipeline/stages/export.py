"""Export the manga rows that qualify for embedding to a Parquet snapshot."""

import os
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import structlog
from sqlalchemy.orm import Session

from manga_recommender.core.config import get_pipeline_settings
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
    batch_size: int,
    description_length: int,
) -> None:
    """Write the export snapshot to `path`, one row group per streamed batch.

    Each `write_batch` call starts a new row group, so `batch_size` also sets
    the row-group size.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(f"{path}_tmp")
    logger.info("export_started", path=str(path), batch_size=batch_size)
    try:
        with pq.ParquetWriter(tmp_path, SCHEMA) as writer:
            exported_count = 0
            for rows in stream_exportable_manga(db, batch_size, description_length):
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
        os.replace(tmp_path, path)
        logger.info(
            "export_completed",
            path=str(path),
            count=exported_count,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def run_export() -> None:
    """Read the qualifying manga and write the Parquet snapshot."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        create_manga_parquet(
            session,
            Path(settings.parquet_path),
            settings.batch_size,
            settings.min_description_length,
        )
