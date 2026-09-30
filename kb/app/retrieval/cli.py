"""CLI for one-off KB searches without starting the API server — used by
`make kb-search q="..."`. Builds/loads the same retrieval index main.py
does, so results match what the API would return.
"""

from __future__ import annotations

import argparse
import json
import sys

from kb.app.retrieval.index_builder import build_index, load_active_records
from kb.app.retrieval.search import build_retrieval_index, hybrid_search
from kb.app.retrieval.vector_store import get_vector_store
from kb.app.settings import REPO_ROOT, get_settings

_KB_RECORDS_PATH = REPO_ROOT / "data" / "processed" / "kb_records.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search the KB from the command line.")
    parser.add_argument("--query", required=True, help="The search query text.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of results (default: KB_TOP_K).")
    parser.add_argument("--category", default=None, help="Optional category filter.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a formatted table.")
    args = parser.parse_args(argv)

    settings = get_settings()
    records = load_active_records(_KB_RECORDS_PATH)
    if not records:
        print(
            f"No active KB records found at {_KB_RECORDS_PATH}. "
            "Run `make ingest-kb` first.",
            file=sys.stderr,
        )
        return 1

    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    if vector_store.count() == 0:
        build_index(records, vector_store, settings.embedding_model)
    index = build_retrieval_index(records, vector_store)

    filters = {"category": args.category} if args.category else None
    response = hybrid_search(args.query, index=index, settings=settings, top_k=args.top_k, filters=filters)

    if args.json:
        print(response.model_dump_json(indent=2))
        return 0

    print(f'Query: "{response.query}"')
    print(f"Grounded: {response.grounded}   Latency: {response.latency_ms:.1f}ms")
    print()
    if not response.results:
        print("No results.")
        return 0
    for i, hit in enumerate(response.results, start=1):
        print(f"{i}. {hit.title}  (dense={hit.dense_score:.3f} bm25={hit.bm25_score:.2f} fused={hit.fused_score:.4f})")
        print(f"   {hit.content[:160]}{'...' if len(hit.content) > 160 else ''}")
        print(f"   {hit.citation}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
