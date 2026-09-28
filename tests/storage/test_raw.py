import gzip
import json
from pathlib import Path

import pytest
import structlog

from manga_recommender.storage.raw import (
    MANIFEST_NAME,
    RawRunWriter,
    latest_complete_run,
    read_manifest,
    read_records,
)


@pytest.fixture
def dataset_path(tmp_path: Path) -> Path:
    return tmp_path / "anilist" / "community_recs"


def _records(count: int) -> list[dict]:
    return [{"id": i, "title": f"タイトル {i}"} for i in range(count)]


def _read_part(run_dir: Path, name: str = "part-00001.jsonl.gz") -> list[dict]:
    with gzip.open(run_dir / name, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_constructing_a_writer_does_not_touch_the_filesystem(dataset_path):
    RawRunWriter(dataset_path)

    assert not dataset_path.exists()


def test_run_dir_sits_under_the_given_path(dataset_path):
    writer = RawRunWriter(dataset_path)

    assert writer.run_dir == dataset_path / f"run={writer.run_id}"
    assert len(writer.run_id) == len("20260928T101500Z")
    assert writer.run_id.endswith("Z")


def test_written_records_read_back_in_order(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        for record in _records(3):
            writer.write(record)
        writer.finish()

    run_dir = latest_complete_run(dataset_path)
    assert run_dir == writer.run_dir
    assert list(read_records(run_dir)) == _records(3)


def test_non_ascii_text_is_stored_as_utf8_not_escaped(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.write({"title": "進撃の巨人"})
        writer.finish()

    part = (writer.run_dir / "part-00001.jsonl.gz").read_bytes()
    assert "進撃の巨人" in gzip.decompress(part).decode("utf-8")


def test_new_part_starts_after_part_size_records(dataset_path):
    with RawRunWriter(dataset_path, part_size=2) as writer:
        for record in _records(5):
            writer.write(record)
        writer.finish()

    manifest = read_manifest(writer.run_dir)
    assert manifest["parts"] == [
        "part-00001.jsonl.gz",
        "part-00002.jsonl.gz",
        "part-00003.jsonl.gz",
    ]
    assert manifest["record_count"] == 5
    assert list(read_records(writer.run_dir)) == _records(5)


def test_manifest_describes_the_run(dataset_path):
    with RawRunWriter(dataset_path, part_size=7) as writer:
        writer.write({"id": 1})
        writer.finish()

    manifest = read_manifest(writer.run_dir)
    assert manifest["run_id"] == writer.run_id
    assert manifest["part_size"] == 7
    assert manifest["started_at"] <= manifest["finished_at"]


def test_finish_stores_extra_fields_in_the_manifest(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.finish(failed_chunks=[[30001, 30050]], chunk_size=50)

    manifest = read_manifest(writer.run_dir)
    assert manifest["failed_chunks"] == [[30001, 30050]]
    assert manifest["chunk_size"] == 50


def test_extra_fields_cannot_overwrite_the_manifest_fields(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})
        writer.finish(record_count=999, parts=[])

    manifest = read_manifest(writer.run_dir)
    assert manifest["record_count"] == 1
    assert manifest["parts"] == ["part-00001.jsonl.gz"]


def test_empty_run_is_complete_and_has_no_records(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.finish()

    assert read_manifest(writer.run_dir)["parts"] == []
    assert list(read_records(writer.run_dir)) == []


def test_run_without_finish_has_no_manifest_and_is_not_found(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})

    assert not (writer.run_dir / MANIFEST_NAME).exists()
    with pytest.raises(FileNotFoundError):
        latest_complete_run(dataset_path)


def test_leaving_the_block_without_finish_logs_a_warning(dataset_path):
    with structlog.testing.capture_logs() as logs, RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})

    assert logs[-1]["event"] == "raw_run_not_finished"
    assert logs[-1]["log_level"] == "warning"


def test_exception_in_block_propagates_and_leaves_a_closed_part(dataset_path):
    with pytest.raises(KeyError), RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})
        raise KeyError("boom")

    assert not (writer.run_dir / MANIFEST_NAME).exists()
    assert _read_part(writer.run_dir) == [{"id": 1}]


def test_latest_complete_run_skips_a_newer_incomplete_run(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.finish()
    (dataset_path / "run=99991231T235959Z").mkdir()

    assert latest_complete_run(dataset_path) == writer.run_dir


def test_latest_complete_run_picks_the_newest_complete_run(dataset_path):
    for run_id in ["20260101T000000Z", "20260928T101500Z", "20260315T120000Z"]:
        run_dir = dataset_path / f"run={run_id}"
        run_dir.mkdir(parents=True)
        (run_dir / MANIFEST_NAME).write_text(json.dumps({"parts": []}))

    assert latest_complete_run(dataset_path) == dataset_path / "run=20260928T101500Z"


def test_latest_complete_run_raises_when_there_are_no_runs(dataset_path):
    with pytest.raises(FileNotFoundError):
        latest_complete_run(dataset_path)


def test_read_records_ignores_parts_the_manifest_does_not_list(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})
        writer.finish()
    with gzip.open(writer.run_dir / "part-00099.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps({"id": "stray"}) + "\n")

    assert list(read_records(writer.run_dir)) == [{"id": 1}]


def test_entering_an_existing_run_dir_fails(dataset_path):
    writer = RawRunWriter(dataset_path)
    writer.run_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError), writer:
        pass


def test_write_after_finish_fails(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.finish()
        with pytest.raises(RuntimeError):
            writer.write({"id": 1})


def test_finish_twice_fails_and_keeps_the_first_manifest(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.write({"id": 1})
        writer.finish()
        first = read_manifest(writer.run_dir)
        with pytest.raises(RuntimeError):
            writer.finish()

    assert read_manifest(writer.run_dir) == first


def test_no_temporary_manifest_is_left_behind(dataset_path):
    with RawRunWriter(dataset_path) as writer:
        writer.finish()

    assert [p.name for p in writer.run_dir.iterdir()] == [MANIFEST_NAME]


@pytest.mark.parametrize("part_size", [0, -1])
def test_part_size_below_one_is_rejected(dataset_path, part_size):
    with pytest.raises(ValueError):
        RawRunWriter(dataset_path, part_size=part_size)
