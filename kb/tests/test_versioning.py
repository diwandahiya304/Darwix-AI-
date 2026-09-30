from pathlib import Path

from kb.app.ingest.versioning import (
    append_changelog,
    bump_patch,
    compute_content_hash,
    load_previous_active_records,
    reconcile_versions,
)
from kb.app.models import KBRecord, KBSourceType, RecordStatus


def _record(record_id: str, content: str, **overrides) -> KBRecord:
    defaults = dict(
        record_id=record_id,
        title="Policy Terms",
        content=content,
        category="policy",
        source_type=KBSourceType.PDF,
        source_ref="raw/pdfs/policy_terms.pdf#page=1",
        version="1.0.0",
        created_at="2025-01-01T00:00:00+00:00",
        updated_at="2025-01-01T00:00:00+00:00",
        content_hash=compute_content_hash(content),
        parent_source_id="abc123",
        chunk_index=0,
    )
    defaults.update(overrides)
    return KBRecord(**defaults)


def test_bump_patch_increments_last_component():
    assert bump_patch("1.0.0") == "1.0.1"
    assert bump_patch("2.3.9") == "2.3.10"


def test_bump_patch_falls_back_on_malformed_version():
    assert bump_patch("not-a-version") == "1.0.0"


def test_compute_content_hash_is_exact_not_normalized():
    # Unlike dedupe.py's whole-document hash, this one is case/whitespace
    # sensitive — any textual change is version-worthy.
    assert compute_content_hash("Hello World") != compute_content_hash("hello world")
    assert compute_content_hash("Hello World") == compute_content_hash("Hello World")


def test_new_record_gets_created_and_updated_timestamps_stamped():
    new = _record("kb_x_000", "Original content.", created_at="", updated_at="")
    final_active, deprecated, changelog = reconcile_versions([new], previous_active={})
    assert len(final_active) == 1
    assert final_active[0].created_at
    assert final_active[0].updated_at
    assert final_active[0].version == "1.0.0"
    assert deprecated == []
    assert changelog == []


def test_unchanged_content_keeps_prior_record_identity():
    prior = _record("kb_x_000", "Same content.", version="1.0.2")
    candidate = _record("kb_x_000", "Same content.")  # fresh build, same content
    final_active, deprecated, changelog = reconcile_versions(
        [candidate], previous_active={"kb_x_000": prior}
    )
    assert final_active == [prior]
    assert deprecated == []
    assert changelog == []


def test_changed_content_bumps_patch_and_deprecates_prior():
    prior = _record("kb_x_000", "Old wording.", version="1.0.0", created_at="2025-01-01T00:00:00+00:00")
    candidate = _record("kb_x_000", "New wording.")
    final_active, deprecated, changelog = reconcile_versions(
        [candidate], previous_active={"kb_x_000": prior}
    )
    assert len(final_active) == 1
    assert final_active[0].version == "1.0.1"
    assert final_active[0].created_at == "2025-01-01T00:00:00+00:00"  # inherited
    assert final_active[0].status == RecordStatus.ACTIVE
    assert len(deprecated) == 1
    assert deprecated[0].record_id == "kb_x_000"
    assert deprecated[0].version == "1.0.0"
    assert deprecated[0].status == RecordStatus.DEPRECATED
    assert len(changelog) == 1
    assert "1.0.0 -> 1.0.1" in changelog[0]


def test_load_previous_active_records_skips_deprecated(tmp_path: Path):
    jsonl_path = tmp_path / "kb_records.jsonl"
    active = _record("kb_a_000", "content a", status=RecordStatus.ACTIVE)
    deprecated = _record("kb_b_000", "content b", status=RecordStatus.DEPRECATED)
    jsonl_path.write_text(
        active.model_dump_json() + "\n" + deprecated.model_dump_json() + "\n", encoding="utf-8"
    )
    result = load_previous_active_records(jsonl_path)
    assert set(result) == {"kb_a_000"}


def test_load_previous_active_records_returns_empty_when_file_missing(tmp_path: Path):
    assert load_previous_active_records(tmp_path / "does_not_exist.jsonl") == {}


def test_append_changelog_creates_file_with_header_then_appends(tmp_path: Path):
    changelog_path = tmp_path / "CHANGELOG.md"
    append_changelog(changelog_path, ["- entry one"])
    append_changelog(changelog_path, ["- entry two"])
    content = changelog_path.read_text(encoding="utf-8")
    assert content.count("# KB Changelog") == 1
    assert "entry one" in content
    assert "entry two" in content


def test_append_changelog_is_a_noop_for_empty_lines(tmp_path: Path):
    changelog_path = tmp_path / "CHANGELOG.md"
    append_changelog(changelog_path, [])
    assert not changelog_path.exists()
