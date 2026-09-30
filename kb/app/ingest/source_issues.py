"""Persist SourceIssue records (extraction failures, obvious source
errors) to data/processed/source_issues.json — never contains PII, only
file/location/issue metadata (CLAUDE.md §7 measurement conventions)."""

from __future__ import annotations

import json
from pathlib import Path

from kb.app.models import SourceIssue


def write_source_issues(issues: list[SourceIssue], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [issue.model_dump() for issue in issues]
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
