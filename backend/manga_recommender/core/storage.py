"""Read and write the artifacts that ingests and pipeline stages share.

Every write goes to a temporary file and replaces `path` only once it is complete,
so a reader never sees a partial file.
"""

import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def write_table(path: Path, table: pa.Table) -> None:
    """Write `table` to a Parquet file."""
    with _replace_when_done(path) as tmp_path:
        pq.write_table(table, tmp_path)


def write_batches(
    path: Path, schema: pa.Schema, batches: Iterable[pa.RecordBatch]
) -> int:
    """Stream `batches` into a Parquet file, one row group each. Return the row count."""
    row_count = 0
    with (
        _replace_when_done(path) as tmp_path,
        pq.ParquetWriter(tmp_path, schema) as writer,
    ):
        for batch in batches:
            writer.write_batch(batch)
            row_count += batch.num_rows
    return row_count


def read_table(path: Path) -> pa.Table:
    """Return a whole Parquet file."""
    return pq.read_table(path)


def read_batches(path: Path, batch_size: int) -> Iterator[pa.RecordBatch]:
    """Yield a Parquet file in batches of up to `batch_size` rows."""
    with pq.ParquetFile(path) as parquet_file:
        yield from parquet_file.iter_batches(batch_size)


def count_rows(path: Path) -> int:
    """Return the row count of a Parquet file without reading its rows."""
    with pq.ParquetFile(path) as parquet_file:
        return parquet_file.metadata.num_rows


def write_arrays(path: Path, **arrays: Any) -> None:
    """Write named arrays to an `.npz` file."""
    with _replace_when_done(path) as tmp_path, tmp_path.open("wb") as file:
        np.savez(file, **arrays)


def read_arrays(path: Path) -> dict[str, np.ndarray]:
    """Return every array of an `.npz` file, keyed by name."""
    with np.load(path) as data:
        return {name: data[name] for name in data.files}


@contextmanager
def _replace_when_done(path: Path) -> Iterator[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        yield tmp_path
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)
