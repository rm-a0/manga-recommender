"""Write raw source data as runs of gzipped JSON Lines parts, and read them back.

A run is complete only when its manifest exists, and the manifest is written last.
"""

import gzip
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self, TextIO

import structlog

from manga_recommender.storage.artifacts import atomic_output

logger = structlog.get_logger(__name__)

MANIFEST_NAME = "manifest.json"


class RawRunWriter:
    """Write the records of one run to `{path}/run={run_id}/`.

    Call `finish()` inside the `with` block. A run without it has no manifest.
    """

    def __init__(self, path: Path, part_size: int = 10_000) -> None:
        """Set the run ID and directory without touching the filesystem."""
        if part_size < 1:
            raise ValueError(f"part_size must be at least 1, got {part_size}")
        self.part_size = part_size
        self.started_at = datetime.now(UTC)
        self.run_id = self.started_at.strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = path / f"run={self.run_id}"
        self.record_count = 0
        self._parts: list[str] = []
        self._part_file: TextIO | None = None
        self._part_record_count = 0
        self._finished = False

    def __enter__(self) -> Self:
        """Create the run directory. Raise `FileExistsError` if the run ID is taken."""
        self.run_dir.mkdir(parents=True, exist_ok=False)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the open part. Never write the manifest here."""
        self._close_part()
        if exc_type is None and not self._finished:
            logger.warning("raw_run_not_finished", run_dir=str(self.run_dir))

    def write(self, record: dict[str, Any]) -> None:
        """Append one record. Start a new part after `part_size` records."""
        if self._finished:
            raise RuntimeError(f"run {self.run_id} is already finished")
        part_file = self._part_file
        if part_file is None or self._part_record_count >= self.part_size:
            part_file = self._open_next_part()
        part_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._part_record_count += 1
        self.record_count += 1

    def finish(self, **extra: Any) -> None:
        """Write the manifest, which marks the run complete. `extra` adds fields to it."""
        if self._finished:
            raise RuntimeError(f"run {self.run_id} is already finished")
        self._close_part()
        manifest = {
            **extra,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "record_count": self.record_count,
            "part_size": self.part_size,
            "parts": self._parts,
        }
        with atomic_output(self.run_dir / MANIFEST_NAME) as tmp_path:
            tmp_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        self._finished = True
        logger.info(
            "raw_run_finished",
            run_dir=str(self.run_dir),
            record_count=self.record_count,
            parts=len(self._parts),
        )

    def _open_next_part(self) -> TextIO:
        self._close_part()
        name = f"part-{len(self._parts) + 1:05d}.jsonl.gz"
        part_file = gzip.open(self.run_dir / name, "wt", encoding="utf-8")  # noqa: SIM115
        self._part_file = part_file
        self._parts.append(name)
        self._part_record_count = 0
        return part_file

    def _close_part(self) -> None:
        if self._part_file is not None:
            self._part_file.close()
            self._part_file = None


def latest_complete_run(path: Path) -> Path:
    """Return the newest run under `path` that has a manifest."""
    complete = [run for run in path.glob("run=*") if (run / MANIFEST_NAME).is_file()]
    if not complete:
        raise FileNotFoundError(f"no complete run under {path}")
    return max(complete)


def read_manifest(run_dir: Path) -> dict[str, Any]:
    """Return the manifest of a complete run."""
    return json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))


def read_records(run_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield every record of a complete run. Read only the parts the manifest lists."""
    for part in read_manifest(run_dir)["parts"]:
        with gzip.open(run_dir / part, "rt", encoding="utf-8") as part_file:
            for line in part_file:
                yield json.loads(line)
