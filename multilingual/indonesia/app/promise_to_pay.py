"""Promise-to-pay ("janji bayar"): the Indonesia market's one business
action beyond the shared search/escalate/callback tools — a standard
collections-industry record of a customer's committed payment date and
amount, used to track follow-up without escalating every unresolved call.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

_SCHEMA = """
CREATE TABLE IF NOT EXISTS promises_to_pay (
    promise_id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL,
    promise_date TEXT NOT NULL,
    amount INTEGER,
    recorded_at TEXT NOT NULL
);
"""


class RecordPromiseToPayArgs(BaseModel):
    loan_id: str
    promise_date: str  # ISO 8601 date
    amount: int | None = None  # IDR


class RecordPromiseToPayResult(BaseModel):
    promise_id: str
    recorded_at: str


def record_promise_to_pay(args: RecordPromiseToPayArgs, db_path: Path) -> RecordPromiseToPayResult:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        promise_id = f"promise_{uuid.uuid4().hex[:12]}"
        recorded_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO promises_to_pay (promise_id, loan_id, promise_date, amount, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (promise_id, args.loan_id, args.promise_date, args.amount, recorded_at),
        )
        conn.commit()
    finally:
        conn.close()
    return RecordPromiseToPayResult(promise_id=promise_id, recorded_at=recorded_at)
