from pathlib import Path

from voice_agent.app.crm import create_lead, get_lead, schedule_callback
from voice_agent.app.models import (
    CreateLeadArgs,
    LeadTemperature,
    ScheduleCallbackArgs,
)


def test_create_lead_round_trips(tmp_path: Path):
    db_path = tmp_path / "crm.sqlite3"
    args = CreateLeadArgs(
        call_id="call_1",
        customer_name="Test Customer",
        phone="9000000000",
        city="Pune",
        age=32,
        family_size=3,
        conditions=None,
        budget=1800,
        intent="interested",
        qualification=LeadTemperature.HOT,
        qualification_reasons=["Age within ideal range.", "Budget comfortable."],
        objections_raised=["premium too expensive"],
        call_summary="Cooperative customer, qualified hot, requested a quote.",
        next_action="send_quote",
    )
    result = create_lead(args, db_path)
    assert result.lead_id.startswith("lead_")

    stored = get_lead(result.lead_id, db_path)
    assert stored is not None
    assert stored["customer_name"] == "Test Customer"
    assert stored["qualification"] == "hot"
    assert "premium too expensive" in stored["objections_raised"]


def test_create_lead_handles_missing_optional_fields(tmp_path: Path):
    db_path = tmp_path / "crm.sqlite3"
    args = CreateLeadArgs(
        qualification=LeadTemperature.COLD,
        call_summary="Out-of-scope call, no qualification collected.",
        next_action="none",
    )
    result = create_lead(args, db_path)
    stored = get_lead(result.lead_id, db_path)
    assert stored["customer_name"] is None
    assert stored["qualification"] == "cold"


def test_get_lead_returns_none_for_unknown_id(tmp_path: Path):
    db_path = tmp_path / "crm.sqlite3"
    assert get_lead("lead_does_not_exist", db_path) is None


def test_schedule_callback_round_trips(tmp_path: Path):
    db_path = tmp_path / "crm.sqlite3"
    args = ScheduleCallbackArgs(
        phone="9000000000",
        requested_datetime="2025-10-05T15:00:00+05:30",
        call_id="call_1",
        notes="Customer asked to be called back after work hours.",
    )
    result = schedule_callback(args, db_path)
    assert result.callback_id.startswith("cb_")
    assert result.confirmed_datetime == "2025-10-05T15:00:00+05:30"


def test_leads_and_callbacks_share_the_same_db_file(tmp_path: Path):
    db_path = tmp_path / "crm.sqlite3"
    create_lead(
        CreateLeadArgs(qualification=LeadTemperature.WARM, call_summary="s", next_action="n"),
        db_path,
    )
    schedule_callback(
        ScheduleCallbackArgs(phone="9000000000", requested_datetime="2025-10-05T15:00:00+05:30"),
        db_path,
    )
    assert db_path.exists()
