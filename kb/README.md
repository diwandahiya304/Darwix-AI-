# kb/ — Production-Ready Knowledge Base (Q2)

> Status: **ingestion pipeline + hybrid retrieval API + eval harness, all
> implemented and run for real against a synthetic dataset.** See Known
> Limitations for what's genuinely thin (the grounding-threshold margin,
> in particular) rather than glossed over.

## Overview

`kb/app/ingest/` turns mixed, messy business content (web pages, PDFs
with tables, policy documents) into short, self-contained, speakable,
versioned KB records (`data/processed/kb_records.jsonl`). `kb/app/
retrieval/` embeds and indexes those records for hybrid dense+BM25
search, exposed as a FastAPI service the Q1 voice agent and Q3
multilingual bots call at answer time — never hardcoded FAQs in a system
prompt. `kb/eval/` measures retrieval quality against real, verified
queries.

## Data Collection and Cleaning

Pipeline stages (`kb/app/ingest/pipeline.py` orchestrates all of them),
run per-page (not whole-document) so a PDF's page number survives all the
way to citation:

1. **Extraction**
   - HTML (`extract_html.py`): `trafilatura`, using its **markdown**
     output format (not plain text) so internal `#`/`##` headings and
     `- ` list markers survive into the cleaned text — the chunker below
     depends on both. Falls back to a BeautifulSoup heuristic (largest
     `<main>`/`<article>`/`<body>` block, headings manually re-marked)
     if trafilatura returns nothing.
   - PDF (`extract_pdf.py`): `pdfplumber` per-page text + tables (tables
     → markdown, inlined into that page's text). A page with neither is
     flagged `extraction_failed`; OCR (`pytesseract` + a page rasterized
     via `pymupdf`) is retried first if available — best-effort, never
     fatal (this dev environment has no Tesseract binary installed; see
     Known Limitations).
   - Every failure/OCR-recovery logs to `data/processed/source_issues.json`
     (repo-relative paths, never absolute — see docs/DECISIONS.md).

2. **Cleaning** (`clean.py`) — residual boilerplate lines and whitespace
   collapse, on top of what extraction already stripped.

3. **Standardization** (`standardize.py`) — dates → ISO 8601; currency →
   canonical `INR <amount>` (handles Indian digit grouping); terminology
   → canonicalized via `kb/config/terminology.yaml`, **case-preserving**
   (a sentence-initial "Sum Insured" becomes "Sum assured", not a
   lowercase mid-sentence-looking "sum assured"); category → mapped onto
   `kb/config/taxonomy.yaml` (three-pass matching: exact, underscore-token
   overlap for compound names, then substring — see docs/DECISIONS.md);
   form field labels → `snake_case`.

4. **PII masking** (`pii.py`) — Presidio pinned to the small
   `en_core_web_sm` model (not its own default `en_core_web_lg`, which
   silently downloads ~587MB on first use), custom Aadhaar/PAN pattern
   recognizers, two NER false-positive fixes (a structured-entity-
   overlap fix and a single-token-PERSON fix — both caught against this
   repo's own synthetic data, not hypothesized), regex-only fallback if
   Presidio isn't available.

5. **Deduplication** (`dedupe.py`) — exact sha256 hash + pairwise Jaccard
   similarity over 5-word shingles (threshold 0.5 — recalibrated from the
   brief's suggested >0.92, which is calibrated for embedding cosine
   similarity, a different metric; see docs/DECISIONS.md). No MinHash/
   LSH library: `datasketch` eagerly imports `scipy`, which conflicts
   with this corpus's PII stack — removing the dependency was simpler
   than fighting three packages' numpy pins, and exact pairwise
   comparison is fast enough at this corpus's scale.

6. **Chunking** (`chunk.py`) — category-aware, not just word-count-based:
   - **faq** → one chunk per Q:/A: pair.
   - **objection_handling** → one chunk per Objection:/Response: pair.
   - **eligibility_qualification** → one chunk per bulleted/numbered rule.
   - everything else → split by heading first, then by sentence boundary,
     targeting 80-200 words per chunk.
   - Falls back to the generic path if a specialized parser finds
     nothing to split on. Every chunk is made self-contained (document
     title, and section heading if any, prepended) since the voice agent
     reads exactly one chunk aloud per turn.

7. **Versioning** (`versioning.py`) — see below.

## PII Handling

See step 4 above; the short version: typed placeholders (`[EMAIL]`,
`[PHONE]`, `[AADHAAR]`, `[PAN]`, `[PERSON]`), `pii`/`pii_types` set on
every record, raw values never logged anywhere —
`docs/q2_kb/pii_report.{md,json}` is counts-by-type only.

## Knowledge-Base Design

**Schema** (`kb.app.models.KBRecord`):

| Field | Example |
|---|---|
| `record_id` | `kb_ffb60c939503aacd_000` (deterministic: `kb_<source_id>_<chunk_index>`, where `source_id` hashes the repo-relative path, not an absolute one — reproducible across machines) |
| `title` | Policy Terms |
| `content` | This policy provides sum assured up to INR 1,000,000... |
| `category` / `subcategory` | `policy` / _(not populated yet — see Known Limitations)_ |
| `source_type` | `policy` (website\|pdf\|form\|faq\|policy — heuristic: category wins for faq/policy, else extraction format + a "form" filename hint) |
| `source_ref` | `raw/pdfs/policy_terms.pdf#page=1` (PDF always cites a page; HTML never does — websites don't have "pages") |
| `source_ids_merged` | ids of any near-duplicate documents merged into this one |
| `version` / `status` | `1.0.0` / `active` — see Versioning |
| `created_at` / `updated_at` | ISO 8601, both set on first ingestion, `updated_at` only on a version bump |
| `pii` / `pii_types` | `false` / `[]` |
| `language` | `en` (fixed for now; Q3 will set this per-market) |
| `audience` | `customer` \| `agent` (heuristic: `compliance_disclosure`/`escalation`-category content is agent-facing) |
| `keywords` | lightweight, dependency-free extraction (terminology-map hits + word-frequency fallback) — supplementary metadata, not part of ranking |
| `content_hash` | sha256 of this exact version's content — drives versioning |

- **Taxonomy** (`kb/config/taxonomy.yaml`): `product`, `policy`,
  `eligibility_qualification`, `faq`, `objection_handling`, `process`,
  `compliance_disclosure`, `escalation`, `uncategorized`. `escalation` has
  no KB content by design — human-escalation handling is a voice-agent
  conversation-flow concern, not something retrieved from a KB (a
  defensible scoping choice, not an oversight).
- **Terminology map** (`kb/config/terminology.yaml`): canonical term →
  synonyms, e.g. `sum_assured: [sum assured, cover amount, coverage
  amount, sum insured]`.

## Versioning

Each pipeline run compares its freshly-built records against the
previous run's *active* records by `record_id` + `content_hash`.
Unchanged content is left untouched (no spurious re-timestamping).
Changed content bumps the **patch** version only (`1.0.0` → `1.0.1`) and
keeps the superseded version in `kb_records.jsonl` with
`status=deprecated` rather than overwriting it — full history stays in
the flat file. Every bump appends a line to `kb/CHANGELOG.md`. Major/minor
bumps are a deliberate human decision (a text diff can't reliably judge
"breaking" vs. "notable"); see docs/DECISIONS.md.

## Retrieval API

FastAPI service (`kb/app/main.py`), built once at startup (not per
request):

- `POST /search` — `{query, top_k?, filters?}` → hybrid dense+BM25
  search fused via Reciprocal Rank Fusion (k=60, the literature-standard
  constant). Returns `grounded: false` (never an invented answer) when
  the top result's **dense cosine similarity** — not the fused RRF score,
  which isn't on a comparable scale — falls below
  `KB_MIN_RELEVANCE_SCORE`. Every result carries a precomputed
  `citation`: `[record_id | source_ref | version]`.
- `GET /record/{id}` — fetch one active record by id, 404 if not found.
- `GET /health` — liveness + how many active records are indexed.

**Embeddings**: `intfloat/multilingual-e5-small` (multilingual so the
same model also serves Q3's Philippines/Indonesia content later), via
direct `transformers`+`torch` — **not** the `sentence-transformers`
wrapper, which has a reproducible bug loading this model's pooling
config in the installed version. Mean-pooling + L2-normalize +
`"query: "`/`"passage: "` prefixing, exactly per the E5 model card.

**Vector store**: swappable via `VECTOR_STORE_BACKEND` (`chroma` |
`qdrant`), both fully local (no server process). Chroma is the default;
Qdrant is implemented and tested too — and its local-mode
`delete_collection()` had a real, reproducible reset bug, fixed with
point-level deletion (see docs/DECISIONS.md).

**Lexical search**: `rank_bm25`, rebuilt at query time (not persisted) —
cheap enough at this corpus's scale to skip the complexity of keeping a
second on-disk index in sync.

## Retrieval Testing

`kb/eval/queries.yaml` (13 queries: 11 in-scope covering every taxonomy
category except `escalation`, 2 out-of-scope) run for real against the
live index by `kb/eval/run_eval.py` (`make kb-eval`), writing
`docs/q2_kb/retrieval_test_results.{md,json}` — user question, retrieved
chunk, source reference, relevance explanation, and verdict
(correct/partially correct/incorrect) per query, plus hit@1, hit@3, and
out-of-scope rejection rate. Verdicts are auto-graded by substring match
against content verified to actually exist in the KB, not hand-picked
after the fact.

**Latest run**: hit@1 = 1.00, hit@3 = 1.00, out-of-scope rejection = 1.00,
latency P50 = 31.1ms / P95 = 77.5ms (well under the 300ms target).

## Synthetic Test Data

`data/raw/` ships with a synthetic dataset
(`kb/app/ingest/synthetic_data.py`, auto-generated by `make ingest-kb` if
`data/raw/` is empty) — every name/phone/PAN/Aadhaar/email in it is
fabricated to exercise PII masking; see `data/raw/SYNTHETIC_DATA_NOTICE.md`.
Filenames are chosen to land in distinct taxonomy categories on purpose,
so every category-aware chunker gets exercised, not just the fallback
path. Also includes: boilerplate (extraction cleanup), a near-duplicate
page (dedup), inconsistent terminology/date/currency formats, a
multi-page PDF with one intentionally blank page (extraction-failure
path), and a table (PDF extraction).

## Setup

```bash
make setup            # from repo root
```

## Run

```bash
make ingest-kb                          # extract -> clean -> mask PII -> dedupe -> chunk -> version
make kb-index                           # (re)build the vector+BM25 index (also runs automatically on first use)
make run-kb                             # start the retrieval API (uvicorn, port $KB_PORT)
make kb-search q="what is the waiting period for pre-existing disease cover"
make kb-eval                            # run the retrieval eval harness
```

## Test

```bash
make test-kb
```

74 tests: ingestion (dedupe, PII masking incl. two real NER-false-
positive regressions, standardization, category-aware chunking,
versioning, one end-to-end pipeline smoke test), retrieval (embeddings —
a real model integration test, not mocked; vector store contract tests
parametrized across both backends; BM25; RRF fusion; a hybrid-search
integration test; a FastAPI wiring smoke test against the real ingested
KB).

## Metrics

`docs/q2_kb/kb_cleaning_report.{md,json}` (ingestion), `pii_report.{md,json}`
(PII counts by type only), `retrieval_test_results.{md,json}` (hit@1/
hit@3/out-of-scope-rejection-rate + latency P50/P95, per-query verdicts).

## Known Limitations

- **The grounding-threshold margin is thin.** `KB_MIN_RELEVANCE_SCORE=0.84`
  was calibrated against ~24 real exploratory queries (in-scope top-1
  scores 0.849-0.937, out-of-scope 0.732-0.829) — a real but only ~0.02
  gap, not a comfortable one. A differently-phrased genuine question
  could plausibly land on the wrong side. See docs/DECISIONS.md for the
  full measurement and honest discussion — this is the single most
  fragile part of the retrieval design and should be named as such, not
  glossed over, in the video walkthrough. A production system should
  consider combining BM25 lexical-overlap agreement into the grounding
  decision, or adding a reranker, rather than a single dense-similarity
  cutoff.
- **`subcategory` is never populated** — the schema has the field, but
  nothing in this KB's content currently has a clean subcategory signal
  to derive it from. Documented as unimplemented, not silently dropped.
- **Category is filename-derived, not content-classified** — works for
  this curated synthetic dataset (filenames double as topic labels),
  wouldn't generalize to arbitrarily-named real source files.
- **OCR fallback needs a system Tesseract install**, which this dev
  environment doesn't have — pages that fail extraction are flagged, not
  silently dropped, but recovery doesn't actually happen here.
- **BM25 is rebuilt per query, not persisted** — fine at this corpus's
  scale (measured: sub-millisecond), would need revisiting at real
  production corpus sizes.
- **Near-duplicate detection is pairwise Jaccard, O(n²)** — same scale
  caveat as BM25.
- **`escalation` has no KB content** — human-escalation handling is
  treated as a voice-agent conversation-flow concern (Q1), not a
  retrievable KB category. Revisit if Q1's design ends up needing
  escalation *policy* content (e.g. "when is escalation mandatory")
  rather than just escalation *behavior*.
