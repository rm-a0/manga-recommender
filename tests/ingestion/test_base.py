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


# --- BBCode removal ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("[i]Italic[/i] text.", "Italic text."),
        ("[b]Bold[/b] text.", "Bold text."),
        ("[u]Under[/u] and [s]struck[/s].", "Under and struck."),
        ("[QUOTE]Cited.[/QUOTE]", "Cited."),
        ("[color=#FF0000]Red[/color] and [size=14]big[/size].", "Red and big."),
    ],
)
def test_description_removes_bbcode_and_keeps_the_text(raw: str, expected: str) -> None:
    """The markup carries no meaning, but the words it wraps do."""
    assert _record(raw).description == expected


def test_description_keeps_the_target_of_a_url_tag():
    """A `[url]` wraps text worth keeping, so only the markers go."""
    raw = "See [url=https://example.com]the site[/url] for more."

    assert _record(raw).description == "See the site for more."


def test_description_drops_an_img_tag_with_its_url():
    """An image URL is not prose, so the whole tag goes."""
    raw = "[img]https://cdn.example.com/cover.png[/img]A real description."

    assert _record(raw).description == "A real description."


def test_description_turns_a_list_bullet_into_a_line_break():
    """`[*]` is the only separator between the list items."""
    raw = "Volumes:[list][*]One[*]Two[/list]"

    assert _record(raw).description == "Volumes:\nOne\nTwo"


@pytest.mark.parametrize(
    "raw",
    [
        "Chapter [1] and [2] are prequels.",
        "The [Written by MAL Rewrite] credit.",
        "Volume [Special Edition] released.",
        "Ratings: [8.5/10] overall.",
        "An unclosed [bracket and more text.",
    ],
)
def test_description_keeps_a_bracket_that_is_not_bbcode(raw: str) -> None:
    """Only the named tags go. A generic `\\[.*\\]` would remove these too."""
    assert _record(raw).description == raw


def test_description_leaves_no_double_space_where_a_tag_was():
    """The markup pass runs before the whitespace pass, so the gap closes."""
    raw = "A story. [img]https://cdn/x.png[/img] The end."

    assert _record(raw).description == "A story. The end."
