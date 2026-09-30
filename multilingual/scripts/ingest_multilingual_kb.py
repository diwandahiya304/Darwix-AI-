"""Ingests the Philippines and Indonesia KB seed content
(multilingual/{philippines,indonesia}/kb_seed/) into the SAME
data/processed/kb_records.jsonl the English Q2 KB uses, tagged with the
correct `language` (fil / id) — reusing kb/'s ingestion pipeline
architecture (extract → clean → standardize → mask PII → dedupe → chunk
→ version) rather than a separate implementation. See
kb/app/ingest/pipeline.py's `extra_raw_dirs` parameter, added
specifically for this.

Language code choice: "fil" (ISO 639-1 code for Filipino, matching Azure
Speech's `fil-PH` locale) — not "tl" (Tagalog). These are very close but
not identical; Deepgram's nova-3 documentation references "tl" for
Tagalog specifically. This is flagged, not resolved with certainty — see
docs/q3_multilingual/asr_report.md and gaps.md.

One retrieval index then serves all three markets — the voice bots in
philippines/ and indonesia/ call the SAME kb/ retrieval API with
`filters={"language": "fil"}` / `{"language": "id"}` to scope results to
their own market's content (see kb/app/retrieval/search.py's
`_record_matches_filters`, already supports this — no kb/ changes needed
beyond the pipeline's language tagging).

Run: `make multilingual-ingest-kb`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from kb.app.ingest.pipeline import RAW_DIR, run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
PHILIPPINES_KB_SEED = REPO_ROOT / "multilingual" / "philippines" / "kb_seed"
INDONESIA_KB_SEED = REPO_ROOT / "multilingual" / "indonesia" / "kb_seed"


def main() -> int:
    report = run_pipeline(
        raw_dir=RAW_DIR,
        raw_dir_language="en",
        extra_raw_dirs={"fil": PHILIPPINES_KB_SEED, "id": INDONESIA_KB_SEED},
    )
    print(f"Ingested {report.counts.docs_in} docs (en + fil + id) -> {report.counts.chunks_out} chunks")
    print(
        f"Exact dup removed: {report.counts.exact_duplicates_removed}, "
        f"near-dup removed: {report.counts.near_duplicates_removed}"
    )
    print(
        f"Extraction failures: {report.counts.extraction_failures}, "
        f"PII records: {report.counts.pii_records}, "
        f"versioned: {report.counts.records_versioned}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
