"""Mock CRM: create_lead / schedule_callback, backed by SQLite
(data/processed/mock_crm.sqlite3 by default — stdlib sqlite3, no new
dependency). A stand-in for a real CRM integration; the schema and
behavior are what matters for this assessment, not a specific vendor API.

The DB file is a derived/regeneratable demo artifact (gitignored, like
kb/'s vector index) that accumulates data from test/simulator runs, which
use only synthetic customer data (see voice_agent/sim/). A production
deployment would need the same PII-handling discipline kb/'s ingestion
pipeline applies to real customer data — see README Known Limitations.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from voice_agent.app.models import (
    CreateLeadArgs,
    CreateLeadResult,
    ScheduleCallbackArgs,
    ScheduleCallbackResult,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    call_id TEXT,
    customer_name TEXT,
    phone TEXT,
    city TEXT,
    age INTEGER,
    family_size INTEGER,
    conditions TEXT,
    budget INTEGER,
    intent TEXT,
    qualification TEXT NOT NULL,
    qualification_reasons TEXT NOT NULL,  -- JSON list
    objections_raised TEXT NOT NULL,      -- JSON list
    call_summary TEXT NOT NULL,
    next_action TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS callbacks (
    callback_id TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    requested_datetime TEXT NOT NULL,
    call_id TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


def create_lead(args: CreateLeadArgs, db_path: Path) -> CreateLeadResult:
    lead_id = f"lead_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO leads (
                lead_id, call_id, customer_name, phone, city, age, family_size,
                conditions, budget, intent, qualification, qualification_reasons,
                objections_raised, call_summary, next_action, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lead_id,
                args.call_id,
                args.customer_name,
                args.phone,
                args.city,
                args.age,
                args.family_size,
                args.conditions,
                args.budget,
                args.intent,
                args.qualification.value,
                json.dumps(args.qualification_reasons),
                json.dumps(args.objections_raised),
                args.call_summary,
                args.next_action,
                created_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return CreateLeadResult(lead_id=lead_id, created_at=created_at)


def schedule_callback(args: ScheduleCallbackArgs, db_path: Path) -> ScheduleCallbackResult:
    callback_id = f"cb_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO callbacks
               (callback_id, phone, requested_datetime, call_id, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (callback_id, args.phone, args.requested_datetime, args.call_id, args.notes, created_at),
        )
        conn.commit()
    finally:
        conn.close()
    return ScheduleCallbackResult(callback_id=callback_id, confirmed_datetime=args.requested_datetime)


def get_lead(lead_id: str, db_path: Path) -> dict | None:
    """Convenience reader — used by tests and, later, docs/report generation."""

    conn = _connect(db_path)
    try:
        cursor = conn.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [d[0] for d in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()
