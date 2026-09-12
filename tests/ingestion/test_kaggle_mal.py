import csv
from datetime import date
from pathlib import Path

import pytest

from manga_recommender.core.config import KaggleMalSettings
from manga_recommender.db.models.manga import MangaStatus, MangaType
from manga_recommender.ingestion.base import NormalizedTag
from manga_recommender.ingestion.extractors.kaggle_mal import KaggleMalExtractor

CSV_FIELDS = [
    "mal_id",
    "title",
    "title_english",
    "type",
    "status",
    "published_from",
    "score",
    "scored_by",
    "authors",
    "serializations",
    "genres",
    "themes",
    "demographics",
    "synopsis",
    "image_url",
]


def _extractor(**settings_overrides) -> KaggleMalExtractor:
    extractor = KaggleMalExtractor()
    extractor.kaggle_mal_settings = KaggleMalSettings(**settings_overrides)
    return extractor


def _row(
    *,
    mal_id: str = "1",
    title: str = "Monster",
    title_english: str = "Monster",
    type: str = "Manga",
    status: str = "Finished",
    published_from: str = "1994-12-05",
    score: str = "9.16",
    scored_by: str = "116668",
    authors: str = "Urasawa, Naoki",
    serializations: str = "Big Comic Original",
    genres: str = "Award Winning|Drama|Mystery",
    themes: str = "Adult Cast|Psychological",
    demographics: str = "Seinen",
    synopsis: str = "A neurosurgeon hunts the monster he once saved.",
    image_url: str = "https://myanimelist.net/images/manga/3/258224.jpg",
) -> dict[str, str]:
    return {
        "mal_id": mal_id,
        "title": title,
        "title_english": title_english,
        "type": type,
        "status": status,
        "published_from": published_from,
        "score": score,
        "scored_by": scored_by,
        "authors": authors,
        "serializations": serializations,
        "genres": genres,
        "themes": themes,
        "demographics": demographics,
        "synopsis": synopsis,
        "image_url": image_url,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --- _extract_status ---


def test_extract_status_maps_known_status():
    extractor = _extractor()

    assert extractor._extract_status(_row(status="Publishing")) == MangaStatus.ONGOING


def test_extract_status_maps_every_dataset_value():
    extractor = _extractor()
    expected = {
        "Finished": MangaStatus.FINISHED,
        "Publishing": MangaStatus.ONGOING,
        "On Hiatus": MangaStatus.HIATUS,
        "Discontinued": MangaStatus.CANCELLED,
    }

    for raw, status in expected.items():
        assert extractor._extract_status(_row(status=raw)) == status


def test_extract_status_returns_none_for_unmapped_status():
    extractor = _extractor()

    assert extractor._extract_status(_row(status="Not yet published")) is None


def test_extract_status_returns_none_when_status_missing():
    extractor = _extractor()

    assert extractor._extract_status({}) is None


# --- _clean_description ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A story. (Source: Tapas)", "A story. "),
        ("A story. (Source : ANN)", "A story. "),
        ("A story. (Source MU, edited)", "A story. "),
        ("A story. (Source-M-U)", "A story. "),
        ("A story. (Source", "A story. "),
        ("Mid (Source: MU) sentence.", "Mid  sentence."),
    ],
)
def test_clean_description_removes_a_source_trailer(raw: str, expected: str) -> None:
    """Contributors write the separator several ways, and the cap can cut it."""
    extractor = _extractor()

    assert extractor._clean_description(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "A story. [Written by MAL Rewrite]",
        "A story. [Written by Denji]",
        "A story. [Written by MA",
    ],
)
def test_clean_description_removes_a_credit_line(raw: str) -> None:
    extractor = _extractor()

    assert extractor._clean_description(raw) == "A story. "


@pytest.mark.parametrize(
    "raw",
    [
        "A story. Included one-shots: Volume 14: The Prototype",
        "A story. Included one-shot Volume 1: Call",
        "A story. included one-shots Wildman Blues",
    ],
)
def test_clean_description_cuts_a_one_shot_list(raw: str) -> None:
    """The list names the volumes a release collects. It describes no story."""
    extractor = _extractor()

    assert extractor._clean_description(raw) == "A story. "


def test_clean_description_unescapes_entities():
    extractor = _extractor()

    assert extractor._clean_description("Cats &amp; Dogs") == "Cats & Dogs"


def test_clean_description_unescapes_a_double_escaped_entity():
    """A few rows went through an escaper twice."""
    extractor = _extractor()

    assert extractor._clean_description("Cats &amp;amp; Dogs") == "Cats & Dogs"


def test_clean_description_keeps_a_plain_synopsis_unchanged():
    extractor = _extractor()
    raw = "A neurosurgeon hunts the monster he once saved."

    assert extractor._clean_description(raw) == raw


def test_extract_description_returns_none_for_an_empty_synopsis():
    extractor = _extractor()

    assert extractor._extract_description(_row(synopsis="")) is None


def test_to_record_cleans_and_tidies_the_synopsis():
    """The extractor removes the source noise, and the record tidies the rest."""
    extractor = _extractor()

    record = extractor._to_record(_row(synopsis="A  story. (Source: Tapas)"))

    assert record.description == "A story."


def test_to_record_reads_a_lone_one_shot_list_as_no_description():
    extractor = _extractor()

    record = extractor._to_record(_row(synopsis="Included one-shots: Volume 1"))

    assert record.description is None


# --- _extract_type ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Manga", MangaType.MANGA),
        ("Manhwa", MangaType.MANHWA),
        ("Manhua", MangaType.MANHUA),
        ("One-shot", MangaType.ONE_SHOT),
        ("Doujinshi", MangaType.DOUJINSHI),
        ("Light Novel", MangaType.LIGHT_NOVEL),
        ("Novel", MangaType.LIGHT_NOVEL),
    ],
)
def test_extract_type_maps_every_dataset_value(raw: str, expected: MangaType) -> None:
    """`Novel` folds into `Light Novel`: the split carries no useful signal."""
    extractor = _extractor()

    assert extractor._extract_type(_row(type=raw)) == expected


def test_extract_type_returns_none_when_unmapped():
    extractor = _extractor()

    assert extractor._extract_type(_row(type="Manhua Comic")) is None


def test_extract_type_returns_none_when_missing():
    extractor = _extractor()

    assert extractor._extract_type({}) is None


# --- _extract_published_date ---


def test_extract_published_date_parses_iso_date():
    extractor = _extractor()

    assert extractor._extract_published_date(_row(published_from="1994-12-05")) == date(
        1994, 12, 5
    )


def test_extract_published_date_returns_none_when_empty():
    extractor = _extractor()

    assert extractor._extract_published_date(_row(published_from="")) is None


def test_extract_published_date_returns_none_when_missing():
    extractor = _extractor()

    assert extractor._extract_published_date({}) is None


# --- _split_pipe ---


def test_split_pipe_splits_and_strips():
    extractor = _extractor()

    assert extractor._split_pipe("Action | Drama|Fantasy ") == [
        "Action",
        "Drama",
        "Fantasy",
    ]


def test_split_pipe_returns_empty_list_for_empty_string():
    extractor = _extractor()

    assert extractor._split_pipe("") == []


# --- _extract_authors ---


def test_extract_authors_splits_on_the_pipe_not_the_comma():
    extractor = _extractor()
    row = _row(authors="Miura, Kentarou|Studio Gaga")

    assert extractor._extract_authors(row) == ["Miura, Kentarou", "Studio Gaga"]


def test_extract_authors_returns_single_author_unchanged():
    extractor = _extractor()

    assert extractor._extract_authors(_row(authors="Urasawa, Naoki")) == [
        "Urasawa, Naoki"
    ]


def test_extract_authors_returns_empty_when_absent():
    extractor = _extractor()

    assert extractor._extract_authors(_row(authors="")) == []


# --- _extract_tags ---


def test_extract_tags_combines_genres_themes_and_demographics():
    extractor = _extractor()
    row = _row(
        genres="Action|Drama",
        themes="Psychological",
        demographics="Seinen",
    )

    assert extractor._extract_tags(row) == [
        NormalizedTag(
            name="Action",
            category="Genre",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Drama",
            category="Genre",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Psychological",
            category="Theme",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Seinen",
            category="Demographic",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
    ]


def test_extract_tags_skips_empty_columns():
    extractor = _extractor()
    row = _row(genres="Action", themes="", demographics="")

    assert extractor._extract_tags(row) == [
        NormalizedTag(
            name="Action",
            category="Genre",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        )
    ]


def test_extract_tags_marks_an_explicit_genre():
    extractor = _extractor()
    row = _row(genres="Hentai|Action", themes="", demographics="")

    tags = extractor._extract_tags(row) or []

    assert [(t.name, t.is_explicit) for t in tags] == [
        ("Hentai", True),
        ("Action", False),
    ]


def test_extract_tags_returns_none_when_every_column_is_empty():
    extractor = _extractor()
    row = _row(genres="", themes="", demographics="")

    assert extractor._extract_tags(row) is None


# --- _extract_int / _extract_float ---


def test_extract_int_parses_value():
    assert _extractor()._extract_int("116668") == 116668


def test_extract_int_returns_none_for_empty_string():
    assert _extractor()._extract_int("") is None


def test_extract_float_parses_value():
    assert _extractor()._extract_float("9.16") == 9.16


def test_extract_float_returns_none_for_empty_string():
    assert _extractor()._extract_float("") is None


# --- _to_record ---


def test_to_record_maps_all_fields():
    extractor = _extractor()
    row = _row(
        mal_id="1",
        title="Monster",
        title_english="Monster",
        status="Finished",
        published_from="1994-12-05",
        score="9.16",
        scored_by="116668",
        authors="Urasawa, Naoki",
        genres="Award Winning|Drama",
        themes="Psychological",
        demographics="Seinen",
        synopsis="A story.",
        image_url="https://myanimelist.net/images/manga/3/258224.jpg",
    )

    record = extractor._to_record(row)

    assert record.external_id == "1"
    assert record.mal_id == 1
    assert record.title == "Monster"
    assert record.title_english == "Monster"
    assert record.type == MangaType.MANGA
    assert record.authors == ["Urasawa, Naoki"]
    assert record.status == MangaStatus.FINISHED
    assert record.published_date == date(1994, 12, 5)
    assert record.description == "A story."
    assert record.image_url == "https://myanimelist.net/images/manga/3/258224.jpg"
    assert record.tags == [
        NormalizedTag(
            name="Award Winning",
            category="Genre",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Drama",
            category="Genre",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Psychological",
            category="Theme",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
        NormalizedTag(
            name="Seinen",
            category="Demographic",
            rank=None,
            is_spoiler=False,
            is_explicit=False,
        ),
    ]
    assert record.raw_score == 9.16
    assert record.raw_scale_max == 10.0
    assert record.votes_count == 116668
    assert record.score_distribution is None
    assert record.fetched_at is not None


def test_to_record_handles_unscored_manga():
    extractor = _extractor()

    record = extractor._to_record(_row(score="", scored_by=""))

    assert record.raw_score is None
    assert record.votes_count is None
    assert record.raw_scale_max == 10.0


def test_to_record_maps_empty_synopsis_to_none():
    extractor = _extractor()

    assert extractor._to_record(_row(synopsis="")).description is None


def test_to_record_maps_empty_image_url_to_none():
    extractor = _extractor()

    assert extractor._to_record(_row(image_url="")).image_url is None


# --- extract (full stream through the sync bridge) ---


def test_extract_yields_one_record_per_row(tmp_path):
    csv_path = _write_csv(
        tmp_path / "kaggle.csv",
        [_row(mal_id="1", title="A"), _row(mal_id="2", title="B")],
    )
    extractor = _extractor(path=str(csv_path))

    records = list(extractor.extract())

    assert sorted(r.external_id for r in records) == ["1", "2"]


def test_extract_skips_rows_that_fail_to_convert(tmp_path):
    csv_path = _write_csv(
        tmp_path / "kaggle.csv",
        [
            _row(mal_id="1", title="ok"),
            _row(mal_id="not-an-int", title="bad"),
            _row(mal_id="3", title="ok"),
        ],
    )
    extractor = _extractor(path=str(csv_path))

    records = list(extractor.extract())

    assert sorted(r.external_id for r in records) == ["1", "3"]


def test_extract_preserves_embedded_newlines_in_synopsis(tmp_path):
    csv_path = _write_csv(
        tmp_path / "kaggle.csv",
        [_row(synopsis="line one\n\nline two")],
    )
    extractor = _extractor(path=str(csv_path))

    (record,) = list(extractor.extract())

    assert record.description == "line one\n\nline two"


def test_to_record_rejects_a_row_without_a_mal_id():
    extractor = _extractor()

    with pytest.raises(ValueError, match="no mal_id"):
        extractor._to_record(_row(mal_id=""))


def test_to_record_rejects_a_row_without_a_title():
    extractor = _extractor()

    with pytest.raises(ValueError, match="no title"):
        extractor._to_record(_row(title="   "))


def test_to_record_reads_a_blank_english_title_as_none():
    extractor = _extractor()

    record = extractor._to_record(_row(title_english="  "))

    assert record.title_english is None
