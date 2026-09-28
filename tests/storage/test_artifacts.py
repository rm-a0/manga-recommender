import numpy as np
import pytest

from manga_recommender.storage.artifacts import atomic_output


def test_successful_block_moves_the_temporary_file_to_the_path(tmp_path):
    path = tmp_path / "artifact.json"

    with atomic_output(path) as tmp:
        tmp.write_text("new")
        assert not path.exists()

    assert path.read_text() == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["artifact.json"]


def test_failing_block_keeps_the_previous_content_and_removes_the_temporary_file(
    tmp_path,
):
    path = tmp_path / "artifact.json"
    path.write_text("old")

    with pytest.raises(RuntimeError, match="boom"), atomic_output(path) as tmp:
        tmp.write_text("half written")
        raise RuntimeError("boom")

    assert path.read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["artifact.json"]


def test_failing_block_before_any_write_leaves_no_file(tmp_path):
    path = tmp_path / "artifact.json"

    with pytest.raises(RuntimeError), atomic_output(path):
        raise RuntimeError("boom")

    assert list(tmp_path.iterdir()) == []


def test_missing_parent_directories_are_created(tmp_path):
    path = tmp_path / "a" / "b" / "artifact.json"

    with atomic_output(path) as tmp:
        tmp.write_text("x")

    assert path.read_text() == "x"


def test_temporary_path_keeps_the_suffix_and_sits_next_to_the_path(tmp_path):
    path = tmp_path / "embeddings.npz"

    with atomic_output(path) as tmp:
        assert tmp.parent == path.parent
        assert tmp.suffix == ".npz"
        assert tmp != path
        tmp.write_bytes(b"")


def test_np_savez_through_the_temporary_path_lands_at_the_exact_path(tmp_path):
    path = tmp_path / "embeddings.npz"

    with atomic_output(path) as tmp:
        np.savez(tmp, values=np.arange(3))

    assert np.load(path)["values"].tolist() == [0, 1, 2]
    assert [p.name for p in tmp_path.iterdir()] == ["embeddings.npz"]
