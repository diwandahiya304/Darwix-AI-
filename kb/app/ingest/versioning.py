"""Versioning: semantic version per KBRecord, bumped on content change.

A record's `record_id` is stable across pipeline runs (derived from
source path + chunk index — see pipeline.py), so re-ingesting unchanged
content reproduces the same record_id with the same content_hash: nothing
to do. When content_hash differs for an existing *active* record_id, the
OLD row is kept in the output with its status flipped to `deprecated`
(never overwritten in place, so the flat-file history stays auditable),
and a NEW row is emitted with the patch version bumped. Every bump
appends one line to kb/CHANGELOG.md.

Only the patch component is bumped automatically. Deciding whether a
content change is "breaking" (major) or "notable" (minor) needs semantic
judgment a text diff can't give us — the pipeline stays conservative and
leaves major/minor bumps to a human editing the stored version by hand if
a change warrants it. See docs/DECISIONS.md.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from kb.app.models import KBRecord, RecordStatus


def compute_content_hash(content: str) -> str:
    """Exact (not normalized) hash of a record's final content — any
    textual change, however small, is a real version-worthy change here,
    unlike the whitespace/case-insensitive hash dedupe.py uses for
    whole-document near-duplicate detection."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def bump_patch(version: str) -> str:
    try:
        major_s, minor_s, patch_s = version.split(".")
        return f"{int(major_s)}.{int(minor_s)}.{int(patch_s) + 1}"
    except (ValueError, AttributeError):
        return "1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reconcile_versions(
    new_records: list[KBRecord], previous_active: dict[str, KBRecord]
) -> tuple[list[KBRecord], list[KBRecord], list[str]]:
    """`new_records` are this run's freshly-built candidates, each already
    carrying a correct content_hash but placeholder version/timestamps.
    `previous_active` maps record_id -> the record that was active as of
    the last run (see load_previous_active_records).

    Returns (final_active, deprecated, changelog_lines):
      - final_active: new_records with version/timestamps reconciled
        against history (unchanged records come back byte-identical to
        their prior row, not just re-timestamped).
      - deprecated: previously-active records this run's changes
        superseded, with status flipped — appended to the written output
        alongside final_active so version history survives in the flat
        file rather than being silently overwritten.
      - changelog_lines: one Markdown line per version bump.
    """

    final_active: list[KBRecord] = []
    deprecated: list[KBRecord] = []
    changelog_lines: list[str] = []
    now = _now()

    for record in new_records:
        prior = previous_active.get(record.record_id)

        if prior is None:
            record.created_at = now
            record.updated_at = now
            final_active.append(record)
            continue

        if prior.content_hash == record.content_hash:
            # Unchanged: keep the prior row's identity (version, timestamps)
            # untouched rather than manufacturing a no-op "update".
            final_active.append(prior)
            continue

        record.version = bump_patch(prior.version)
        record.created_at = prior.created_at
        record.updated_at = now
        final_active.append(record)

        deprecated.append(
            prior.model_copy(update={"status": RecordStatus.DEPRECATED, "updated_at": now})
        )
        changelog_lines.append(
            f"- {now} — `{record.record_id}` {prior.version} -> {record.version} "
            f"(content changed; previous version marked deprecated)"
        )

    return final_active, deprecated, changelog_lines


def load_previous_active_records(jsonl_path: Path) -> dict[str, KBRecord]:
    if not jsonl_path.exists():
        return {}
    result: dict[str, KBRecord] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = KBRecord.model_validate_json(line)
        if record.status == RecordStatus.ACTIVE:
            result[record.record_id] = record
    return result


def append_changelog(changelog_path: Path, lines: list[str]) -> None:
    if not lines:
        return
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    if not changelog_path.exists():
        changelog_path.write_text(
            "# KB Changelog\n\n"
            "Appended automatically by `make ingest-kb` "
            "(kb.app.ingest.pipeline) whenever a record's content changes "
            "between runs — see kb/README.md Versioning.\n\n",
            encoding="utf-8",
        )
    with changelog_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
