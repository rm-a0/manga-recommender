from datetime import UTC, datetime

import pytest

from manga_recommender.ingestion.base import NormalizedMangaRecord


def _record(description: str | None) -> NormalizedMangaRecord:
    """Build a record that carries only the description under test."""
    return NormalizedMangaRecord(
        external_id="1",
        mal_id=None,
        title="Test Manga",
        title_english=None,
        type=None,
        authors=[],
        status=None,
        description=description,
        tags=None,
        published_date=None,
        raw_score=None,
        raw_scale_max=None,
        votes_count=None,
        score_distribution=None,
        fetched_at=datetime.now(UTC),
        image_url=None,
    )


# --- description normalization ---


def test_description_collapses_spaces_and_tabs():
    assert _record("  A story.\t Here.  ").description == "A story. Here."


def test_description_keeps_one_paragraph_break():
    """The detail page shows this text, so the paragraphs stay."""
    assert _record("One. \n\n\n\n Two.").description == "One.\n\nTwo."


def test_description_normalizes_windows_line_breaks():
    assert _record("One.\r\n\r\nTwo.").description == "One.\n\nTwo."


@pytest.mark.parametrize("raw", ["None.", "N/A", "n/a", "-", "---", ".", "   ", ""])
def test_description_reads_a_placeholder_as_none(raw: str) -> None:
    """`description IS NOT NULL` must mean the row holds a description."""
    assert _record(raw).description is None


def test_description_keeps_a_missing_description_none():
    assert _record(None).description is None


def test_description_leaves_clean_text_unchanged():
    text = "A neurosurgeon hunts the monster he once saved."

    assert _record(text).description == text
