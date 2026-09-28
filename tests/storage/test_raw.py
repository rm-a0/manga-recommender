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

SOURCE = "anilist"
DATASET = "community_recs"


def _writer(root: Path, part_size: int = 10_000) -> RawRunWriter:
    return RawRunWriter(root, SOURCE, DATASET, part_size=part_size)


def _records(count: int) -> list[dict]:
    return [{"id": i, "title": f"タイトル {i}"} for i in range(count)]


def test_constructing_a_writer_does_not_touch_the_filesystem(tmp_path):
    writer = _writer(tmp_path)

    assert not writer.run_dir.exists()
    assert not (tmp_path / SOURCE).exists()


def test_run_dir_uses_source_dataset_and_utc_run_id(tmp_path):
    writer = _writer(tmp_path)

    assert writer.run_dir == tmp_path / SOURCE / DATASET / f"run={writer.run_id}"
    assert writer.run_id.endswith("Z")
    assert len(writer.run_id) == len("20260928T101500Z")


def test_written_records_read_back_in_order(tmp_path):
    records = _records(3)

    with _writer(tmp_path) as writer:
        for record in records:
            writer.write(record)
        writer.finish()

    run_dir = latest_complete_run(tmp_path, SOURCE, DATASET)
    assert run_dir == writer.run_dir
    assert list(read_records(run_dir)) == records


def test_non_ascii_text_is_stored_as_utf8_not_escaped(tmp_path):
    with _writer(tmp_path) as writer:
        writer.write({"title": "進撃の巨人"})
        writer.finish()

    with gzip.open(writer.run_dir / "part-00001.jsonl.gz", "rt", encoding="utf-8") as f:
        assert "進撃の巨人" in f.read()


def test_new_part_starts_after_part_size_records(tmp_path):
    with _writer(tmp_path, part_size=2) as writer:
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


def test_manifest_describes_the_run(tmp_path):
    with _writer(tmp_path, part_size=7) as writer:
        writer.write({"id": 1})
        writer.finish()

    manifest = read_manifest(writer.run_dir)
    assert manifest["source"] == SOURCE
    assert manifest["dataset"] == DATASET
    assert manifest["run_id"] == writer.run_id
    assert manifest["part_size"] == 7
    assert manifest["started_at"] <= manifest["finished_at"]


def test_finish_stores_extra_fields_in_the_manifest(tmp_path):
    with _writer(tmp_path) as writer:
        writer.finish(failed_chunks=[[30001, 30050]], chunk_size=50)

    manifest = read_manifest(writer.run_dir)
    assert manifest["failed_chunks"] == [[30001, 30050]]
    assert manifest["chunk_size"] == 50


def test_finish_rejects_extra_fields_that_overwrite_manifest_fields(tmp_path):
    with (
        _writer(tmp_path) as writer,
        pytest.raises(ValueError, match="record_count"),
    ):
        writer.finish(record_count=999)

    # The failed finish must leave the run incomplete.
    assert not (writer.run_dir / MANIFEST_NAME).exists()


def test_empty_run_is_complete_and_has_no_records(tmp_path):
    with _writer(tmp_path) as writer:
        writer.finish()

    assert read_manifest(writer.run_dir)["parts"] == []
    assert list(read_records(writer.run_dir)) == []


def test_run_without_finish_has_no_manifest_and_is_not_found(tmp_path):
    with _writer(tmp_path) as writer:
        writer.write({"id": 1})

    assert not (writer.run_dir / MANIFEST_NAME).exists()
    with pytest.raises(FileNotFoundError):
        latest_complete_run(tmp_path, SOURCE, DATASET)


def test_leaving_the_block_without_finish_logs_a_warning(tmp_path):
    with structlog.testing.capture_logs() as logs, _writer(tmp_path) as writer:
        writer.write({"id": 1})

    assert {"event": "raw_run_not_finished", "log_level": "warning"}.items() <= logs[
        -1
    ].items()


def test_exception_in_block_propagates_and_leaves_no_manifest(tmp_path):
    with pytest.raises(KeyError), _writer(tmp_path) as writer:
        writer.write({"id": 1})
        raise KeyError("boom")

    assert not (writer.run_dir / MANIFEST_NAME).exists()
    # The part was closed, so it holds a readable gzip stream.
    with gzip.open(writer.run_dir / "part-00001.jsonl.gz", "rt", encoding="utf-8") as f:
        assert [json.loads(line) for line in f] == [{"id": 1}]


def test_latest_complete_run_skips_a_newer_incomplete_run(tmp_path):
    with _writer(tmp_path) as writer:
        writer.write({"id": 1})
        writer.finish()
    newer_incomplete = tmp_path / SOURCE / DATASET / "run=99991231T235959Z"
    newer_incomplete.mkdir()

    assert latest_complete_run(tmp_path, SOURCE, DATASET) == writer.run_dir


def test_latest_complete_run_picks_the_newest_complete_run(tmp_path):
    dataset_dir = tmp_path / SOURCE / DATASET
    for run_id in ["20260101T000000Z", "20260928T101500Z", "20260315T120000Z"]:
        run_dir = dataset_dir / f"run={run_id}"
        run_dir.mkdir(parents=True)
        (run_dir / MANIFEST_NAME).write_text(json.dumps({"parts": []}))

    assert latest_complete_run(tmp_path, SOURCE, DATASET) == (
        dataset_dir / "run=20260928T101500Z"
    )


def test_latest_complete_run_raises_when_the_dataset_has_no_runs(tmp_path):
    with pytest.raises(FileNotFoundError):
        latest_complete_run(tmp_path, SOURCE, DATASET)


def test_read_records_ignores_parts_the_manifest_does_not_list(tmp_path):
    with _writer(tmp_path) as writer:
        writer.write({"id": 1})
        writer.finish()
    with gzip.open(writer.run_dir / "part-00099.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps({"id": "stray"}) + "\n")

    assert list(read_records(writer.run_dir)) == [{"id": 1}]


def test_entering_an_existing_run_dir_fails_loudly(tmp_path):
    writer = _writer(tmp_path)
    writer.run_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError), writer:
        pass


def test_write_after_finish_fails(tmp_path):
    with _writer(tmp_path) as writer:
        writer.finish()
        with pytest.raises(RuntimeError):
            writer.write({"id": 1})


def test_finish_twice_fails_and_keeps_the_first_manifest(tmp_path):
    with _writer(tmp_path) as writer:
        writer.write({"id": 1})
        writer.finish()
        first = read_manifest(writer.run_dir)
        with pytest.raises(RuntimeError):
            writer.finish()

    assert read_manifest(writer.run_dir) == first


def test_no_temporary_manifest_is_left_behind(tmp_path):
    with _writer(tmp_path) as writer:
        writer.finish()

    assert sorted(p.name for p in writer.run_dir.iterdir()) == [MANIFEST_NAME]


@pytest.mark.parametrize("part_size", [0, -1])
def test_part_size_below_one_is_rejected(tmp_path, part_size):
    with pytest.raises(ValueError):
        _writer(tmp_path, part_size=part_size)
