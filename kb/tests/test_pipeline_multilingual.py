"""Tests kb.app.ingest.pipeline's multi-language extension
(extra_raw_dirs) — used by multilingual/ to ingest Philippines/Indonesia
KB seed content into the SAME kb_records.jsonl / retrieval index as the
English KB, tagged with the correct `language`, filterable at query time.
"""

from __future__ import annotations

import json
from pathlib import Path

from kb.app.ingest.pipeline import run_pipeline


def _write_html(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{body}</p></body></html>", encoding="utf-8")


def test_extra_raw_dirs_tags_records_with_the_correct_language(tmp_path: Path):
    en_dir = tmp_path / "en_raw"
    fil_dir = tmp_path / "fil_raw"
    id_dir = tmp_path / "id_raw"

    _write_html(en_dir / "faq_test.html", "FAQ Test", "This is English FAQ content about waiting periods.")
    _write_html(
        fil_dir / "faq_test.html",
        "FAQ Test PH",
        "Ito po ay Tagalog na FAQ na tungkol sa waiting period ng inyong polisiya.",
    )
    _write_html(
        id_dir / "faq_test.html",
        "FAQ Test ID",
        "Ini adalah konten FAQ Bahasa Indonesia tentang masa tunggu polis asuransi.",
    )

    report = run_pipeline(
        raw_dir=en_dir,
        raw_dir_language="en",
        extra_raw_dirs={"fil": fil_dir, "id": id_dir},
        processed_dir=tmp_path / "processed",
        docs_dir=tmp_path / "docs",
        kb_records_path=tmp_path / "processed" / "kb_records.jsonl",
        changelog_path=tmp_path / "CHANGELOG.md",
    )

    assert report.counts.docs_in == 3

    records = [
        json.loads(line)
        for line in (tmp_path / "processed" / "kb_records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    languages_seen = {r["language"] for r in records}
    assert languages_seen == {"en", "fil", "id"}

    # Each market's language tag is on the record it actually came from.
    fil_records = [r for r in records if r["language"] == "fil"]
    assert fil_records
    assert any("Tagalog" in r["content"] or "polisiya" in r["content"] for r in fil_records)

    id_records = [r for r in records if r["language"] == "id"]
    assert id_records
    assert any("Bahasa Indonesia" in r["content"] or "asuransi" in r["content"] for r in id_records)


def test_report_includes_one_example_per_language(tmp_path: Path):
    en_dir = tmp_path / "en_raw"
    fil_dir = tmp_path / "fil_raw"
    _write_html(en_dir / "product_test.html", "Product Test", "English product content.")
    _write_html(fil_dir / "product_test.html", "Produkto Test", "Nilalaman ng produkto sa Tagalog.")

    report = run_pipeline(
        raw_dir=en_dir,
        raw_dir_language="en",
        extra_raw_dirs={"fil": fil_dir},
        processed_dir=tmp_path / "processed",
        docs_dir=tmp_path / "docs",
        kb_records_path=tmp_path / "processed" / "kb_records.jsonl",
        changelog_path=tmp_path / "CHANGELOG.md",
    )

    languages_in_examples = {ex.note.split("language=")[1].split(",")[0] for ex in report.examples}
    assert languages_in_examples == {"en", "fil"}
