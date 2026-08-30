import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_recommender.config import KaggleMalSettings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.base import NormalizedTag
from manga_recommender.ingestion.extractors.kaggle_mal import KaggleMalExtractor

CSV_FIELDS = [
    "mal_id",
    "title",
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


# --- _extract_published_date ---


def test_extract_published_date_parses_iso_date_as_utc():
    extractor = _extractor()

    assert extractor._extract_published_date(
        _row(published_from="1994-12-05")
    ) == datetime(1994, 12, 5, tzinfo=UTC)


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
        NormalizedTag(name="Action", category="Genre", rank=None, is_spoiler=False),
        NormalizedTag(name="Drama", category="Genre", rank=None, is_spoiler=False),
        NormalizedTag(
            name="Psychological", category="Theme", rank=None, is_spoiler=False
        ),
        NormalizedTag(
            name="Seinen", category="Demographic", rank=None, is_spoiler=False
        ),
    ]


def test_extract_tags_skips_empty_columns():
    extractor = _extractor()
    row = _row(genres="Action", themes="", demographics="")

    assert extractor._extract_tags(row) == [
        NormalizedTag(name="Action", category="Genre", rank=None, is_spoiler=False)
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
    assert record.authors == ["Urasawa, Naoki"]
    assert record.status == MangaStatus.FINISHED
    assert record.published_date == datetime(1994, 12, 5, tzinfo=UTC)
    assert record.description == "A story."
    assert record.image_url == "https://myanimelist.net/images/manga/3/258224.jpg"
    assert record.tags == [
        NormalizedTag(
            name="Award Winning", category="Genre", rank=None, is_spoiler=False
        ),
        NormalizedTag(name="Drama", category="Genre", rank=None, is_spoiler=False),
        NormalizedTag(
            name="Psychological", category="Theme", rank=None, is_spoiler=False
        ),
        NormalizedTag(
            name="Seinen", category="Demographic", rank=None, is_spoiler=False
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
