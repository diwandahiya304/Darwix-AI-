"""Optional semantic-similarity helper for app/controller.py's duplicate
suppression — reuses kb/'s already-loaded multilingual-e5-small embedding
model (kb/app/retrieval/embeddings.py) rather than loading a second model
just for this. Returns None on any failure (model not loadable, empty
text, etc.) so a hiccup here degrades to "semantic dedup skipped for this
nudge," never a pipeline crash — the same never-let-an-external-dependency
break the core flow posture as voice_agent's kb_client."""

from __future__ import annotations

_EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"


def embed_for_dedup(text: str) -> list[float] | None:
    if not text.strip():
        return None
    try:
        from kb.app.retrieval.embeddings import embed_query

        return embed_query(text, _EMBEDDING_MODEL_NAME)
    except Exception:
        return None
