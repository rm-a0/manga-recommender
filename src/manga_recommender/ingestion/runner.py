import itertools
import sys
import uuid

from manga_recommender.config import get_ingestion_settings
from manga_recommender.db.repositories.sources import get_or_create_source
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.loader import load_batch
from manga_recommender.ingestion.registry import (
    get_extractor_for_source,
    get_source_weight,
)


def seed_source(source_name: str) -> uuid.UUID:
    """Ensure that the given source is present in the database, creating it if needed."""
    with session_scope() as session:
        return get_or_create_source(
            session,
            name=source_name,
            weight=get_source_weight(source_name),
        ).id


def run_ingestion(sources: list[str]) -> None:
    """Run the ingestion pipeline for the given list of source names."""
    batch_size = get_ingestion_settings().batch_size
    for source in sources:
        try:
            print(f"Running ingestion for source: {source}")
            source_id = seed_source(source)
            extractor = get_extractor_for_source(source)
            for batch in itertools.batched(extractor.extract(), batch_size):
                load_batch(list(batch), source_id)
        except Exception as e:
            print(f"Error during ingestion for source {source}: {e}", file=sys.stderr)
