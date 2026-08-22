"""Base extractor interface and the normalized manga record shape."""

import asyncio
import queue
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from datetime import datetime

from pydantic.dataclasses import dataclass

from manga_recommender.db.models.manga import MangaStatus

_SENTINEL = object()


@dataclass
class NormalizedMangaRecord:
    """Manga data in a source-independent shape, ready for loading."""

    external_id: str
    mal_id: int | None
    title: str
    author: str
    status: MangaStatus | None
    description: str | None
    genres: list[str] | None
    published_date: datetime | None
    raw_score: float | None
    raw_scale_max: float | None
    votes_count: int | None
    score_distribution: list[int] | None
    fetched_at: datetime


class BaseExtractor(ABC):
    """Interface for extractors that pull manga data from an external source."""

    source_name: str

    @abstractmethod
    def _stream(self) -> AsyncIterator[NormalizedMangaRecord]:
        """Yield normalized manga records asynchronously, as they arrive."""
        ...

    def extract(self) -> Iterator[NormalizedMangaRecord]:
        """Run `_stream()` on a background thread and yield its records here.

        Bridges the async producer to this thread through a bounded queue, so
        a slow consumer applies backpressure instead of buffering the whole
        source in memory.
        """
        q: queue.Queue = queue.Queue(maxsize=100)
        error: BaseException | None = None

        async def _drain() -> None:
            async for record in self._stream():
                q.put(record)

        def _run() -> None:
            nonlocal error
            try:
                asyncio.run(_drain())
            except BaseException as e:
                error = e
            finally:
                q.put(_SENTINEL)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        while (item := q.get()) is not _SENTINEL:
            yield item
        thread.join()
        if error is not None:
            raise error
