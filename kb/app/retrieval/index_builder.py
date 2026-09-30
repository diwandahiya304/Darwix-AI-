"""Builds the retrieval indexes (vector store + BM25) from
data/processed/kb_records.jsonl's *active* records (deprecated versions
are excluded — see kb/app/ingest/versioning.py). Run via `make kb-index`,
or automatically the first time the API/CLI starts and finds an empty
vector store.
"""

from __future__ import annotations

import sys
from pathlib import Path

from kb.app.ingest.versioning import load_previous_active_records
from kb.app.models import KBRecord
from kb.app.retrieval.embeddings import embed_passages
from kb.app.retrieval.vector_store import VectorStore, get_vector_store
from kb.app.settings import REPO_ROOT, get_settings

_BATCH_SIZE = 16
_KB_RECORDS_PATH = REPO_ROOT / "data" / "processed" / "kb_records.jsonl"


def load_active_records(kb_records_path: Path) -> dict[str, KBRecord]:
    """Reuses versioning.py's "what's currently active" reader — reading
    the flat file and filtering to status==active is exactly the same
    operation whether the caller is about to compare it against a new
    pipeline run or about to build a search index from it."""

    return load_previous_active_records(kb_records_path)


def build_index(
    records: dict[str, KBRecord], vector_store: VectorStore, embedding_model: str
) -> int:
    """Embeds every record's content ("passage: " prefixed — see
    embeddings.py) and upserts into the vector store, batched so a large
    corpus doesn't require one giant model call. Returns how many records
    were indexed."""

    vector_store.reset()
    record_list = list(records.values())
    for i in range(0, len(record_list), _BATCH_SIZE):
        batch = record_list[i : i + _BATCH_SIZE]
        embeddings = embed_passages([r.content for r in batch], embedding_model)
        vector_store.upsert(
            ids=[r.record_id for r in batch],
            embeddings=embeddings,
            metadatas=[
                {
                    "category": r.category,
                    "audience": r.audience.value,
                    "language": r.language,
                    "source_type": r.source_type.value,
                }
                for r in batch
            ],
            documents=[r.content for r in batch],
        )
    return len(record_list)


def main() -> int:
    settings = get_settings()
    records = load_active_records(_KB_RECORDS_PATH)
    if not records:
        print(f"No active records found at {_KB_RECORDS_PATH} — run `make ingest-kb` first.")
        return 1
    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    count = build_index(records, vector_store, settings.embedding_model)
    print(f"Indexed {count} active records into {settings.vector_store_backend} "
          f"at {settings.vector_store_path_abs()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
