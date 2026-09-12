"""Base extractor interface and the normalized manga record shape."""

import asyncio
import queue
import re
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from manga_recommender.db.models.manga import MangaStatus, MangaType

_SENTINEL = object()

_SPACES_RE = re.compile(r"[^\S\n]+")
_LINE_EDGE_RE = re.compile(r" *\n *")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_PLACEHOLDER_RE = re.compile(r"(?i)^(none\.?|n/?a|-{1,3}|\.)$")


@dataclass
class NormalizedTag:
    """Tag data in a source-independent shape, ready for loading."""

    name: str
    category: str | None
    rank: int | None
    is_spoiler: bool
    is_explicit: bool


@dataclass
class NormalizedMangaRecord:
    """Manga data in a source-independent shape, ready for loading."""

    external_id: str
    mal_id: int | None
    title: str
    title_english: str | None
    type: MangaType | None
    authors: list[str]
    status: MangaStatus | None
    description: str | None
    tags: list[NormalizedTag] | None
    published_date: date | None
    raw_score: float | None
    raw_scale_max: float | None
    votes_count: int | None
    score_distribution: list[int] | None
    fetched_at: datetime
    image_url: str | None

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        """Tidy the whitespace, and read a text that says nothing as None.

        Paragraph breaks stay, because the detail page shows this text. Each
        extractor removes its own source noise before this runs.
        """
        if value is None:
            return None
        text = _SPACES_RE.sub(" ", value.replace("\r\n", "\n"))
        text = _LINE_EDGE_RE.sub("\n", text)
        text = _BLANK_LINES_RE.sub("\n\n", text).strip()
        if not text or _PLACEHOLDER_RE.match(text):
            return None
        return text


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
