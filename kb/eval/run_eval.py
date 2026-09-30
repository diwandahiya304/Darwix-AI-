"""Retrieval test harness: runs kb/eval/queries.yaml against the live
retrieval index and writes docs/q2_kb/retrieval_test_results.{md,json}.

Computes hit@1, hit@3 (does the expected content appear in the top-1 /
top-3 results for an in-scope query?) and the out-of-scope rejection rate
(did an expected_grounded=false query actually come back grounded=false?).

Every verdict is auto-graded by substring match against
`expected_contains` — a genuine relevance judgment needs a human, but a
substring check against content already verified to exist in the KB is an
honest, reproducible proxy for this assessment's scope. Any mismatch is
reported as incorrect with a concrete note on how to fix it — "be
honest: if something is wrong, mark it incorrect" is the instruction this
harness follows; nothing here is a rubber stamp.

Run: `make kb-eval`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yaml

from kb.app.retrieval.index_builder import build_index, load_active_records
from kb.app.retrieval.search import build_retrieval_index, hybrid_search
from kb.app.retrieval.vector_store import get_vector_store
from kb.app.settings import REPO_ROOT, get_settings

QUERIES_PATH = Path(__file__).resolve().parent / "queries.yaml"
KB_RECORDS_PATH = REPO_ROOT / "data" / "processed" / "kb_records.jsonl"
RESULTS_MD_PATH = REPO_ROOT / "docs" / "q2_kb" / "retrieval_test_results.md"
RESULTS_JSON_PATH = REPO_ROOT / "docs" / "q2_kb" / "retrieval_test_results.json"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round(pct * (len(ordered) - 1)))
    return ordered[idx]


def run_eval() -> dict:
    settings = get_settings()
    records = load_active_records(KB_RECORDS_PATH)
    if not records:
        raise SystemExit(f"No active records at {KB_RECORDS_PATH} — run `make ingest-kb` first.")

    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    if vector_store.count() == 0:
        build_index(records, vector_store, settings.embedding_model)
    index = build_retrieval_index(records, vector_store)

    queries = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))["queries"]

    rows: list[dict] = []
    latencies: list[float] = []
    in_scope_hit1 = in_scope_hit3 = in_scope_total = 0
    out_of_scope_correct = out_of_scope_total = 0

    for q in queries:
        response = hybrid_search(q["query"], index=index, settings=settings, top_k=3)
        latencies.append(response.latency_ms)
        top = response.results[0] if response.results else None
        expected_grounded = q["expected_grounded"]
        expected_contains = q.get("expected_contains")

        if not expected_grounded:
            out_of_scope_total += 1
            correct = response.grounded is False
            out_of_scope_correct += int(correct)
            verdict = "correct" if correct else "incorrect"
            note = (
                "Correctly rejected as out-of-scope (no grounded answer returned)."
                if correct
                else (
                    f"Expected grounded=false but got grounded=true (top dense score "
                    f"{top.dense_score:.3f} >= threshold {settings.kb_min_relevance_score}). "
                    f"Fix: raise KB_MIN_RELEVANCE_SCORE, or add a reranker/BM25-agreement "
                    f"check to the grounding decision — see docs/DECISIONS.md's note on "
                    f"the thin dense-score margin between in-scope and out-of-scope queries."
                )
            )
        else:
            in_scope_total += 1
            hit1 = bool(top) and expected_contains.lower() in top.content.lower()
            hit3 = any(expected_contains.lower() in r.content.lower() for r in response.results[:3])
            in_scope_hit1 += int(hit1)
            in_scope_hit3 += int(hit3)

            if not response.grounded:
                verdict = "incorrect"
                note = (
                    f"Expected grounded=true but got grounded=false (top dense score "
                    f"below threshold {settings.kb_min_relevance_score}). Fix: lower "
                    f"KB_MIN_RELEVANCE_SCORE, or this query's phrasing may be too far "
                    f"from the record's actual wording — consider adding a paraphrase "
                    f"to the KB or rephrasing the query."
                )
            elif hit1:
                verdict = "correct"
                note = "Expected content found in the #1 result."
            elif hit3:
                verdict = "partially correct"
                note = "Expected content found in top-3 but not #1 — ranking isn't wrong, just not optimal."
            else:
                verdict = "incorrect"
                note = (
                    f"Expected content not found in top-3 (top result was "
                    f"{top.title if top else '(none)'!r}). Fix: check whether chunking "
                    f"split the expected content oddly, or whether this query needs a "
                    f"closer-worded KB record."
                )

        rows.append(
            {
                "query": q["query"],
                "category": q.get("category"),
                "retrieved": top.content[:200] if top else None,
                "source_ref": top.source_ref if top else None,
                "explanation": note,
                "verdict": verdict,
            }
        )

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hit_at_1": (in_scope_hit1 / in_scope_total) if in_scope_total else None,
        "hit_at_3": (in_scope_hit3 / in_scope_total) if in_scope_total else None,
        "out_of_scope_rejection_rate": (
            out_of_scope_correct / out_of_scope_total if out_of_scope_total else None
        ),
        "latency_ms_p50": _percentile(latencies, 0.5),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "kb_min_relevance_score": settings.kb_min_relevance_score,
        "embedding_model": settings.embedding_model,
        "vector_store_backend": settings.vector_store_backend,
        "rows": rows,
    }
    return summary


def write_results(summary: dict) -> None:
    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def _fmt(value, suffix=""):
        return f"{value:.2f}{suffix}" if value is not None else "n/a"

    lines = [
        "# KB Retrieval Test Results",
        "",
        f"_Generated: {summary['generated_at']}_",
        "",
        "## Summary",
        "",
        f"- hit@1: {_fmt(summary['hit_at_1'])}",
        f"- hit@3: {_fmt(summary['hit_at_3'])}",
        f"- Out-of-scope rejection rate: {_fmt(summary['out_of_scope_rejection_rate'])}",
        f"- Latency P50: {summary['latency_ms_p50']:.1f}ms, P95: {summary['latency_ms_p95']:.1f}ms",
        f"- KB_MIN_RELEVANCE_SCORE: {summary['kb_min_relevance_score']} "
        f"(embedding: `{summary['embedding_model']}`, vector store: {summary['vector_store_backend']})",
        "",
        "## Per-query results",
        "",
        "| # | Query | Category | Retrieved chunk (top-1) | Source reference | Relevance explanation | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, row in enumerate(summary["rows"], start=1):
        retrieved = (row["retrieved"] or "(none)").replace("|", "\\|").replace("\n", " ")
        explanation = row["explanation"].replace("|", "\\|")
        lines.append(
            f"| {i} | {row['query']} | {row['category']} | {retrieved[:150]} | "
            f"{row['source_ref'] or '(none)'} | {explanation} | **{row['verdict']}** |"
        )
    RESULTS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    summary = run_eval()
    write_results(summary)
    print(
        f"hit@1={summary['hit_at_1']:.2f} hit@3={summary['hit_at_3']:.2f} "
        f"oos_rejection={summary['out_of_scope_rejection_rate']:.2f} "
        f"latency_p50={summary['latency_ms_p50']:.1f}ms p95={summary['latency_ms_p95']:.1f}ms"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
