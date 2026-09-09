from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from manga_recommender.core.config import get_pipeline_settings


def generate_embeddings(
    texts: list[str],
    model_name: str,
    device: str | None,
) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device=device)
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def build_embedding_text(title: str, description: str, tags: list[str]) -> str:
    return title + " " + description + " " + ",".join(tags)


def create_manga_embeddings(
    parquet_path: Path,
    embeddings_path: Path,
    batch_size: int,
    model_name: str,
    device: str | None,
) -> None:
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    ids: list[str] = []
    texts: list[str] = []
    for batch in pq.ParquetFile(parquet_path).iter_batches(batch_size):
        for row in batch.to_pylist():
            ids.extend(row["id"])
            texts.extend(
                build_embedding_text(row["title"], row["description"], row["tags"])
            )
    vectors = generate_embeddings(texts, model_name, device)
    np.savez(embeddings_path, ids=ids, vectors=np.concatenate(vectors))


def run_embed() -> None:
    settings = get_pipeline_settings()
    create_manga_embeddings(
        parquet_path=Path(settings.parquet_path),
        embeddings_path=Path(settings.embeddings_path),
        batch_size=settings.parquet_batch_size,
        model_name=settings.model_name,
        device=settings.device,
    )
