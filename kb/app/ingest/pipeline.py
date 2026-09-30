"""End-to-end KB ingestion pipeline: extract -> clean -> standardize ->
mask PII -> dedupe -> chunk -> version -> write KB records + reports.

Run: `python -m kb.app.ingest.pipeline` (equivalently `make ingest-kb`).
If data/raw/ has no .html or .pdf files yet, a synthetic dataset is
generated first so the pipeline always has something to run against.

Per-page processing (not whole-document): clean/standardize/PII-masking
run on each RawDocument.pages entry independently so a PDF's page number
survives all the way to KBRecord.source_ref (`file#page=N`). Dedup still
compares whole documents (CleanedDocument.joined_text()) since that's a
document-level concern. Versioning compares each new run's KBRecords
against the previous run's active records by record_id + content_hash —
see kb/app/ingest/versioning.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kb.app.ingest.chunk import chunk_document
from kb.app.ingest.clean import clean_text
from kb.app.ingest.dedupe import dedupe_documents
from kb.app.ingest.extract_html import extract_html
from kb.app.ingest.extract_pdf import extract_pdf
from kb.app.ingest.keywords import extract_keywords
from kb.app.ingest.pii import mask_pii
from kb.app.ingest.source_issues import write_source_issues
from kb.app.ingest.standardize import (
    apply_terminology,
    canonicalize_category,
    infer_source_type,
    load_taxonomy,
    load_terminology_map,
    standardize_currency,
    standardize_dates,
    to_title_case,
)
from kb.app.ingest.versioning import (
    append_changelog,
    compute_content_hash,
    load_previous_active_records,
    reconcile_versions,
)
from kb.app.models import (
    Audience,
    BeforeAfterExample,
    CleanedDocument,
    CleanedPage,
    ExtractionFormat,
    KBRecord,
    KBSourceType,
    PipelineCounts,
    PipelineReport,
    RawDocument,
    SourceIssue,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DOCS_DIR = REPO_ROOT / "docs" / "q2_kb"
KB_RECORDS_PATH = PROCESSED_DIR / "kb_records.jsonl"
CHANGELOG_PATH = REPO_ROOT / "kb" / "CHANGELOG.md"

# Categories whose content is written for the agent handling a call, not
# read aloud to the customer — a heuristic, see kb/README.md.
_AGENT_FACING_CATEGORIES = {"compliance_disclosure", "escalation"}


def extract_all(raw_dir: Path) -> tuple[list[RawDocument], list[SourceIssue]]:
    """Extracts every .html/.pdf under raw_dir. Reported paths (in
    RawDocument.source_path, SourceIssue.file, and the source_id hash
    derived from them) are relative to raw_dir's parent (e.g.
    "raw/web/x.html"), not absolute — so source_issues.json/
    kb_records.jsonl stay portable across machines and don't leak local
    filesystem structure.
    """

    docs: list[RawDocument] = []
    issues: list[SourceIssue] = []
    for path in sorted(raw_dir.rglob("*")):
        if path.is_dir():
            continue
        suffix = path.suffix.lower()
        rel_path = str(path.relative_to(raw_dir.parent)).replace("\\", "/")
        if suffix in (".html", ".htm"):
            doc, doc_issues = extract_html(path.read_text(encoding="utf-8"), rel_path)
        elif suffix == ".pdf":
            doc, doc_issues = extract_pdf(str(path), display_path=rel_path)
        else:
            continue
        docs.append(doc)
        issues.extend(doc_issues)
    return docs, issues


def _infer_audience(category: str) -> Audience:
    return Audience.AGENT if category in _AGENT_FACING_CATEGORIES else Audience.CUSTOMER


def build_cleaned_documents(
    raw_docs: list[RawDocument],
    terminology_map: dict[str, str],
    taxonomy: list[str],
    language: str = "en",
) -> tuple[list[CleanedDocument], dict[str, int]]:
    cleaned: list[CleanedDocument] = []
    pii_counts_total: dict[str, int] = {}

    for raw in raw_docs:
        raw_category = Path(raw.source_path).stem
        category = canonicalize_category(raw_category, taxonomy)
        title = to_title_case(raw.title or raw_category.replace("_", " "))
        source_type = infer_source_type(raw.source_path, raw.source_type, category)

        cleaned_pages: list[CleanedPage] = []
        doc_pii_types: set[str] = set()
        for i, page_text in enumerate(raw.pages, start=1):
            text = clean_text(page_text)
            text = standardize_dates(text)
            text = standardize_currency(text)
            text = apply_terminology(text, terminology_map)

            mask_result = mask_pii(text, language=language)
            for pii_type, count in mask_result.counts.items():
                pii_counts_total[pii_type] = pii_counts_total.get(pii_type, 0) + count
            doc_pii_types.update(mask_result.pii_types)

            cleaned_pages.append(
                CleanedPage(
                    page_number=i,
                    text=mask_result.masked_text,
                    pii=bool(mask_result.pii_types),
                    pii_types=mask_result.pii_types,
                )
            )

        cleaned.append(
            CleanedDocument(
                source_id=raw.source_id,
                source_path=raw.source_path,
                title=title,
                category=category,
                source_type=source_type,
                pages=cleaned_pages,
                language=language,
                pii=bool(doc_pii_types),
                pii_types=sorted(doc_pii_types),
            )
        )
    return cleaned, pii_counts_total


def _extraction_format_of(doc: CleanedDocument) -> ExtractionFormat:
    # PDF-origin source_types always carry page numbers in citations;
    # website/faq/policy sourced from HTML never do (see build_kb_records).
    return (
        ExtractionFormat.PDF
        if doc.source_type in (KBSourceType.PDF, KBSourceType.FORM)
        else ExtractionFormat.HTML
    )


def build_kb_records(
    cleaned_docs: list[CleanedDocument], terminology_map: dict[str, str]
) -> list[KBRecord]:
    records: list[KBRecord] = []
    for doc in cleaned_docs:
        is_pdf = _extraction_format_of(doc) == ExtractionFormat.PDF
        chunk_index = 0
        for page in doc.pages:
            chunks = chunk_document(page.text, category=doc.category, title=doc.title)
            source_ref = (
                f"{doc.source_path}#page={page.page_number}" if is_pdf else doc.source_path
            )
            for chunk_content in chunks:
                records.append(
                    KBRecord(
                        record_id=f"kb_{doc.source_id}_{chunk_index:03d}",
                        title=doc.title if chunk_index == 0 else f"{doc.title} (cont.)",
                        content=chunk_content,
                        category=doc.category,
                        source_type=doc.source_type,
                        source_ref=source_ref,
                        source_ids_merged=list(doc.merged_source_ids),
                        created_at="",  # stamped by reconcile_versions
                        updated_at="",
                        language=doc.language,
                        pii=page.pii,
                        pii_types=page.pii_types,
                        audience=_infer_audience(doc.category),
                        keywords=extract_keywords(chunk_content, terminology_map),
                        content_hash=compute_content_hash(chunk_content),
                        parent_source_id=doc.source_id,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
    return records


def write_kb_records(records: list[KBRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda r: (r.record_id, r.version))
    with out_path.open("w", encoding="utf-8") as f:
        for record in ordered:
            f.write(record.model_dump_json() + "\n")


def write_pii_report(pii_counts: dict[str, int], out_path_md: Path, out_path_json: Path) -> None:
    out_path_md.parent.mkdir(parents=True, exist_ok=True)
    out_path_json.write_text(json.dumps(pii_counts, indent=2), encoding="utf-8")

    lines = [
        "# PII Report",
        "",
        "Counts by type across all ingested sources. No raw PII values are",
        "recorded here, or anywhere in the processed KB.",
        "",
        "| PII type | Count |",
        "|---|---|",
    ]
    for pii_type, count in sorted(pii_counts.items()):
        lines.append(f"| {pii_type} | {count} |")
    if not pii_counts:
        lines.append("| _(none detected)_ | 0 |")
    out_path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cleaning_report(report: PipelineReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# KB Cleaning Report",
        "",
        f"_Generated: {report.generated_at}_",
        "",
        "## Summary",
        "",
        f"- Documents in: {report.counts.docs_in}",
        f"- Chunks out: {report.counts.chunks_out}",
        f"- Exact duplicates removed: {report.counts.exact_duplicates_removed}",
        f"- Near-duplicates removed: {report.counts.near_duplicates_removed}",
        f"- Extraction failures flagged: {report.counts.extraction_failures}",
        f"- Records containing PII: {report.counts.pii_records}",
        f"- Records versioned this run: {report.counts.records_versioned}",
        "",
        "## PII found (by type)",
        "",
    ]
    if report.pii_counts_by_type:
        lines += ["| Type | Count |", "|---|---|"]
        lines += [f"| {t} | {c} |" for t, c in sorted(report.pii_counts_by_type.items())]
    else:
        lines.append("_(none detected)_")

    lines += ["", "## Before / After Examples", ""]
    for i, ex in enumerate(report.examples, start=1):
        lines += [f"### Example {i} -- `{ex.source_id}`", ""]
        if ex.note:
            lines += [f"_{ex.note}_", ""]
        lines += [
            "**Before:**",
            "```",
            ex.before[:600],
            "```",
            "",
            "**After:**",
            "```",
            ex.after[:600],
            "```",
            "",
        ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    raw_dir: Path = RAW_DIR,
    raw_dir_language: str = "en",
    extra_raw_dirs: dict[str, Path] | None = None,
    processed_dir: Path = PROCESSED_DIR,
    docs_dir: Path = DOCS_DIR,
    kb_records_path: Path | None = None,
    changelog_path: Path | None = None,
) -> PipelineReport:
    """`raw_dir`/`raw_dir_language` is the primary (default: English)
    source directory — unchanged behavior from before multi-language
    support existed (synthetic data auto-generates here if empty).
    `extra_raw_dirs` (e.g. `{"fil": ..., "id": ...}`, used by
    multilingual/) adds more language-tagged directories processed in the
    same run, so a single kb_records.jsonl / retrieval index ends up
    covering every market, filterable by `language` at query time (see
    kb/app/retrieval/search.py's `filters=`). Each directory's KBRecords
    get `language` stamped from its own entry in this map — see
    build_cleaned_documents/build_kb_records.
    """

    kb_records_path = kb_records_path or (processed_dir / "kb_records.jsonl")
    changelog_path = changelog_path or CHANGELOG_PATH

    raw_dir_map: dict[str, Path] = {raw_dir_language: raw_dir}
    if extra_raw_dirs:
        raw_dir_map.update(extra_raw_dirs)

    if (
        raw_dir_language == "en"
        and not any(raw_dir.rglob("*.html"))
        and not any(raw_dir.rglob("*.pdf"))
    ):
        from kb.app.ingest.synthetic_data import generate_synthetic_dataset

        generate_synthetic_dataset(raw_dir)

    terminology_map = load_terminology_map()
    taxonomy = load_taxonomy()

    all_raw_docs: list[RawDocument] = []
    all_issues: list[SourceIssue] = []
    all_cleaned: list[CleanedDocument] = []
    pii_counts: dict[str, int] = {}
    before_snapshots: dict[str, str] = {}

    for language, a_raw_dir in raw_dir_map.items():
        raw_docs, issues = extract_all(a_raw_dir)
        all_raw_docs.extend(raw_docs)
        all_issues.extend(issues)
        before_snapshots.update({d.source_id: "\n\n".join(d.pages)[:600] for d in raw_docs})

        cleaned_docs, batch_pii_counts = build_cleaned_documents(
            raw_docs, terminology_map, taxonomy, language=language
        )
        all_cleaned.extend(cleaned_docs)
        for pii_type, count in batch_pii_counts.items():
            pii_counts[pii_type] = pii_counts.get(pii_type, 0) + count

    dedupe_result = dedupe_documents(
        all_cleaned, get_id=lambda d: d.source_id, get_text=lambda d: d.joined_text()
    )
    for kept_doc in dedupe_result.kept:
        kept_doc.merged_source_ids = dedupe_result.merged_source_ids.get(kept_doc.source_id, [])

    candidate_records = build_kb_records(dedupe_result.kept, terminology_map)

    previous_active = load_previous_active_records(kb_records_path)
    final_active, deprecated, changelog_lines = reconcile_versions(
        candidate_records, previous_active
    )
    append_changelog(changelog_path, changelog_lines)
    all_records = final_active + deprecated

    write_source_issues(all_issues, processed_dir / "source_issues.json")
    write_kb_records(all_records, kb_records_path)
    write_pii_report(pii_counts, docs_dir / "pii_report.md", docs_dir / "pii_report.json")

    # One representative before/after example per language, not just the
    # first 3 documents overall (which, with English processed first,
    # would otherwise crowd out every other market from the report).
    examples: list[BeforeAfterExample] = []
    seen_languages: set[str] = set()
    for doc in all_cleaned:
        if doc.language in seen_languages:
            continue
        seen_languages.add(doc.language)
        examples.append(
            BeforeAfterExample(
                source_id=doc.source_id,
                before=before_snapshots.get(doc.source_id, ""),
                after=doc.joined_text()[:600],
                note=(
                    f"category={doc.category}, source_type={doc.source_type.value}, "
                    f"language={doc.language}, pii={doc.pii}"
                ),
            )
        )

    report = PipelineReport(
        counts=PipelineCounts(
            docs_in=len(all_raw_docs),
            chunks_out=len(final_active),
            exact_duplicates_removed=dedupe_result.exact_duplicates_removed,
            near_duplicates_removed=dedupe_result.near_duplicates_removed,
            extraction_failures=sum(1 for i in all_issues if i.issue_type == "extraction_failed"),
            pii_records=sum(1 for r in final_active if r.pii),
            records_versioned=len(changelog_lines),
        ),
        pii_counts_by_type=pii_counts,
        examples=examples,
    )
    write_cleaning_report(report, docs_dir / "kb_cleaning_report.md")
    (docs_dir / "kb_cleaning_report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    report = run_pipeline()
    print(f"Ingested {report.counts.docs_in} docs -> {report.counts.chunks_out} chunks")
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
