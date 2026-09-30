"""Embeddings: intfloat/multilingual-e5-small via direct transformers+
torch (mean-pooling + L2-normalize), NOT the `sentence-transformers`
wrapper — the installed sentence-transformers==6.1.0 has a reproducible
bug loading this model's pooling config
(`Pooling.__init__() missing 1 required positional argument:
'embedding_dimension'`). This module implements the exact recipe the E5
model card specifies by hand instead: mean-pool the last hidden state
over the attention mask, L2-normalize, and prefix every input with
"query: " or "passage: " depending on which side of a search it's on —
E5 models are trained with that prefix convention and retrieval quality
degrades noticeably without it. See docs/DECISIONS.md.

Multilingual (not an English-only model like bge-small-en-v1.5) so the
same embedding space also serves Q3's Philippines/Indonesia content
later, per the assignment brief's explicit ask.

The model is a process-wide lazy singleton (like kb.app.ingest.pii's
Presidio analyzer) — loading it takes several seconds, so it happens once
per process, not once per call.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")

_tokenizer = None
_model = None
_model_name: str | None = None


def _load(model_name: str):
    global _tokenizer, _model, _model_name
    if _model is not None and _model_name == model_name:
        return
    import torch  # noqa: F401  (import guard: torch must be installed)
    from transformers import AutoModel, AutoTokenizer

    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _model = AutoModel.from_pretrained(model_name)
    _model.eval()
    _model_name = model_name


def _embed(texts: list[str], model_name: str):
    import torch

    _load(model_name)
    inputs = _tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        out = _model(**inputs)
    last_hidden = out.last_hidden_state
    mask = inputs["attention_mask"].unsqueeze(-1).float()
    pooled = (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
    return normalized.tolist()


def embed_queries(texts: list[str], model_name: str) -> list[list[float]]:
    return _embed([f"query: {t}" for t in texts], model_name)


def embed_passages(texts: list[str], model_name: str) -> list[list[float]]:
    return _embed([f"passage: {t}" for t in texts], model_name)


def embed_query(text: str, model_name: str) -> list[float]:
    return embed_queries([text], model_name)[0]
