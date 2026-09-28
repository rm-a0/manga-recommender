"""Write artifacts so that a reader never sees a partial file."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_output(path: Path) -> Iterator[Path]:
    """Yield a temporary path, and move it to `path` when the block succeeds.

    When the block raises, delete the temporary file. `path` then keeps its
    previous content. The temporary name keeps the suffix of `path`, because
    some writers, such as `np.savez`, add a suffix when it is missing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    try:
        yield tmp_path
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)
