import pytest

from manga_recommender.ingestion.extractors.anilist import AnilistExtractor
from manga_recommender.ingestion.registry import (
    get_all_registered_sources,
    get_extractor_for_source,
    get_source_weight,
)


def test_get_all_registered_sources_includes_anilist() -> None:
    assert "anilist" in get_all_registered_sources()


def test_get_extractor_for_source_returns_extractor_instance() -> None:
    extractor = get_extractor_for_source("anilist")

    assert isinstance(extractor, AnilistExtractor)


def test_get_extractor_for_source_raises_for_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown source"):
        get_extractor_for_source("no-such-source")


def test_get_source_weight_returns_registered_weight() -> None:
    assert get_source_weight("anilist") == 1.0


def test_get_source_weight_raises_for_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown source"):
        get_source_weight("no-such-source")
