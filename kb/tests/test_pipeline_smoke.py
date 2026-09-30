"""End-to-end smoke test: runs the whole ingestion pipeline against the
synthetic dataset in an isolated tmp_path (never touches the real
data/raw|processed, docs/q2_kb, or kb/CHANGELOG.md), and checks the
invariants that matter most: records get produced across every
category-aware chunker, near-duplicates get merged, no raw synthetic PII
value survives into the processed KB, and re-running the pipeline against
unchanged input doesn't spuriously bump versions.
"""

import json
from pathlib import Path

from kb.app.ingest.pipeline import run_pipeline


def _run(tmp_path: Path):
    return run_pipeline(
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        docs_dir=tmp_path / "docs",
        kb_records_path=tmp_path / "processed" / "kb_records.jsonl",
        changelog_path=tmp_path / "CHANGELOG.md",
    )


def test_pipeline_runs_end_to_end_on_synthetic_data(tmp_path: Path):
    report = _run(tmp_path)

    assert report.counts.docs_in > 0
    assert report.counts.chunks_out > 0
    # The synthetic dataset includes a deliberate near-duplicate HTML page.
    assert report.counts.near_duplicates_removed >= 1

    records_path = tmp_path / "processed" / "kb_records.jsonl"
    assert records_path.exists()
    lines = records_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == report.counts.chunks_out

    all_content = "\n".join(lines)
    for raw_pii_value in (
        "ramesh.kumar@example.com",
        "9876543210",
        "priya.sharma@example.com",
        "ABCDE1234F",
        "1234 5678 9012",
        "sunita.rao@example.com",
        "BXPRA5678K",
    ):
        assert raw_pii_value not in all_content

    records = [json.loads(line) for line in lines]
    categories_seen = set()
    for record in records:
        assert record["record_id"]
        assert record["content"]
        assert record["category"]
        assert record["source_type"] in ("website", "pdf", "form", "faq", "policy")
        assert record["source_ref"]
        assert record["version"] == "1.0.0"  # first run: nothing to bump yet
        assert record["status"] == "active"
        assert record["content_hash"]
        categories_seen.add(record["category"])

    # Every category-aware chunker (faq, objection_handling,
    # eligibility_qualification) and the generic heading-aware path
    # (product, process, policy) should be exercised by the synthetic
    # dataset, not just the fallback path.
    assert {"faq", "objection_handling", "eligibility_qualification"} <= categories_seen

    # PDF-origin records cite a page number; HTML-origin ones don't.
    pdf_refs = [r["source_ref"] for r in records if r["source_type"] in ("pdf", "form")]
    assert pdf_refs and all("#page=" in ref for ref in pdf_refs)
    html_refs = [r["source_ref"] for r in records if r["source_type"] in ("website", "faq")]
    assert html_refs and all("#page=" not in ref for ref in html_refs)

    assert (tmp_path / "processed" / "source_issues.json").exists()
    issues = json.loads((tmp_path / "processed" / "source_issues.json").read_text(encoding="utf-8"))
    assert any(
        i["issue_type"] in ("extraction_failed", "extraction_recovered_via_ocr") for i in issues
    )

    assert (tmp_path / "docs" / "kb_cleaning_report.md").exists()
    assert (tmp_path / "docs" / "kb_cleaning_report.json").exists()
    assert (tmp_path / "docs" / "pii_report.md").exists()
    assert (tmp_path / "docs" / "pii_report.json").exists()

    pii_counts = json.loads((tmp_path / "docs" / "pii_report.json").read_text(encoding="utf-8"))
    assert sum(pii_counts.values()) > 0


def test_rerunning_on_unchanged_input_does_not_bump_versions(tmp_path: Path):
    first = _run(tmp_path)
    second = _run(tmp_path)

    assert second.counts.chunks_out == first.counts.chunks_out
    assert second.counts.records_versioned == 0
    assert not (tmp_path / "CHANGELOG.md").exists()

    records_path = tmp_path / "processed" / "kb_records.jsonl"
    versions = {json.loads(line)["version"] for line in records_path.read_text(encoding="utf-8").splitlines()}
    assert versions == {"1.0.0"}
