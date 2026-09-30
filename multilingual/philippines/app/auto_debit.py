"""Auto-debit preference: the Philippines market's one business action
beyond the shared search/escalate/callback tools — records whether a
customer wants premium auto-debit enrollment (and their preferred
payment day). This is the concrete outcome the premium-reminder call
exists to drive toward: avoiding a lapsed policy."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

_SCHEMA = """
CREATE TABLE IF NOT EXISTS auto_debit_preferences (
    preference_id TEXT PRIMARY KEY,
    policy_number TEXT NOT NULL,
    enroll INTEGER NOT NULL,
    payment_day INTEGER,
    recorded_at TEXT NOT NULL
);
"""


class SetAutoDebitArgs(BaseModel):
    policy_number: str
    enroll: bool
    payment_day: int | None = None  # day of month, 1-28


class SetAutoDebitResult(BaseModel):
    preference_id: str
    recorded_at: str


def set_auto_debit_preference(args: SetAutoDebitArgs, db_path: Path) -> SetAutoDebitResult:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        preference_id = f"autodebit_{uuid.uuid4().hex[:12]}"
        recorded_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO auto_debit_preferences "
            "(preference_id, policy_number, enroll, payment_day, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (preference_id, args.policy_number, int(args.enroll), args.payment_day, recorded_at),
        )
        conn.commit()
    finally:
        conn.close()
    return SetAutoDebitResult(preference_id=preference_id, recorded_at=recorded_at)
