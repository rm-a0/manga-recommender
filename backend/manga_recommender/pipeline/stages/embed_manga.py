"""Encode the exported manga rows and write the vectors to an artifact."""

import hashlib
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog

from manga_recommender.core import storage
from manga_recommender.core.config import get_pipeline_settings, get_storage_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = structlog.get_logger(__name__)


def load_model(model_name: str, device: str | None) -> SentenceTransformer:
    """Return the sentence-transformer model that `model_name` names.

    Imports `sentence_transformers` here, not at module scope, so the stage
    registry can import this module without the `ml` dependency group.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device)


def build_embedding_text(title: str, description: str, tags: list[str]) -> str:
    """Return the one string that the model reads for a single manga.

    A change to this template changes every vector, so it needs a full re-run
    of this stage and of `load_embeddings`.
    """
    parts: list[str] = []
    if description:
        parts.append(f"Description: {description}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    if title:
        parts.append(f"Title: {title}")
    return "\n".join(parts)


def _parse_batch(batch: list[Any]) -> tuple[list[str], list[str], list[str]]:
    """Return the ids, model input texts and text hashes of one batch.

    The three lists share one order, so the caller can hold them as parallel
    artifact columns.
    """
    ids: list[str] = []
    texts: list[str] = []
    hashes: list[str] = []
    for row in batch:
        text = build_embedding_text(row["title"], row["description"], row["tags"])
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        ids.append(row["id"])
        hashes.append(text_hash)
        texts.append(text)
    return ids, texts, hashes


def _encode_texts(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
) -> np.ndarray:
    """Return one unit-length vector for each text, as a float32 array.

    `batch_size` sets how many texts the model reads in one forward pass.
    """
    return model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )


def _load_npz_to_dicts(
    path: Path,
    model_name: str,
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Read a previous artifact and return its vectors and hashes, keyed by id.

    Returns two empty dictionaries when `path` holds no artifact, or when the
    artifact comes from a different model. The caller then encodes every row.
    """
    if not path.exists():
        logger.info("previous_artifact_skipped", path=str(path), reason="missing")
        return {}, {}
    data = storage.read_arrays(path)
    if "model_name" not in data or data["model_name"] != model_name:
        logger.info("previous_artifact_skipped", path=str(path), reason="model_changed")
        return {}, {}
    ids = data["ids"]
    vectors = data["vectors"]
    hashes = data["hashes"]
    logger.info("previous_artifact_loaded", path=str(path), count=len(ids))

    vector_dict = {id_: vector for id_, vector in zip(ids, vectors, strict=True)}
    hash_dict = {id_: hash_ for id_, hash_ in zip(ids, hashes, strict=True)}
    return vector_dict, hash_dict


def create_manga_embeddings(
    parquet_path: Path,
    embeddings_path: Path,
    parquet_batch_size: int,
    encode_batch_size: int,
    model_name: str,
    device: str | None,
) -> None:
    """Read the export snapshot and write every vector to `embeddings_path`.

    `parquet_batch_size` sets how many rows each Parquet read returns.
    `encode_batch_size` sets how many texts the model reads in one pass.

    Reuses the vector of a row whose text hash matches the previous artifact,
    so only the new and the changed rows reach the model.
    """
    logger.info(
        "embed_manga_started",
        path=str(embeddings_path),
        model=model_name,
        batch_size=encode_batch_size,
    )

    if storage.count_rows(parquet_path) == 0:
        raise ValueError(f"{parquet_path} holds no rows, nothing to embed")

    model = load_model(model_name, device)
    vector_dict, hash_dict = _load_npz_to_dicts(embeddings_path, model_name)

    dim = model.get_embedding_dimension()
    if dim is None:
        raise ValueError(f"{model_name} reports no embedding dimension")

    chunks: list[np.ndarray] = []
    ids: list[str] = []
    hashes: list[str] = []
    reused_count = 0
    encoded_count = 0

    for batch in storage.read_batches(parquet_path, parquet_batch_size):
        start_time = time.monotonic()
        batch_ids, batch_texts, batch_hashes = _parse_batch(batch.to_pylist())

        encode_pos: list[int] = []
        encode_texts: list[str] = []
        out = np.empty((len(batch_ids), dim), dtype=np.float32)
        zip_batch = zip(batch_ids, batch_texts, batch_hashes, strict=True)
        for pos, (id_, text, text_hash) in enumerate(zip_batch):
            if hash_dict.get(id_) == text_hash:
                out[pos] = vector_dict[id_]
            else:
                encode_pos.append(pos)
                encode_texts.append(text)

        if encode_texts:
            out[encode_pos] = _encode_texts(model, encode_texts, encode_batch_size)

        chunks.append(out)
        ids.extend(batch_ids)
        hashes.extend(batch_hashes)
        reused_count += len(batch_ids) - len(encode_pos)
        encoded_count += len(encode_pos)
        logger.info(
            "batch_embedded",
            count=len(batch_ids),
            reused=len(batch_ids) - len(encode_pos),
            encoded=len(encode_pos),
            elapsed_s=round(time.monotonic() - start_time, 1),
        )

    storage.write_arrays(
        embeddings_path,
        model_name=model_name,
        ids=ids,
        hashes=hashes,
        vectors=np.concatenate(chunks),
    )
    logger.info(
        "embed_manga_completed",
        path=str(embeddings_path),
        count=len(ids),
        reused=reused_count,
        encoded=encoded_count,
    )


def run_embed_manga() -> None:
    """Read the export snapshot and write the embeddings artifact."""
    settings = get_pipeline_settings()
    paths = get_storage_settings()
    create_manga_embeddings(
        parquet_path=paths.manga_snapshot_path,
        embeddings_path=paths.embeddings_path,
        parquet_batch_size=settings.parquet_batch_size,
        encode_batch_size=settings.encode_batch_size,
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )
