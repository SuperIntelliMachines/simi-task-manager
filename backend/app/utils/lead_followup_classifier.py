"""Lead follow-up KPI classification for the Insurance dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.verticals import InsuranceLead
from app.services.insurance_service import OPEN_LEAD_STATUSES
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive

FOLLOWUP_DUE_WINDOW_HOURS = 48


def is_open_lead(lead: InsuranceLead) -> bool:
    return (getattr(lead, "status", None) or "").lower() in OPEN_LEAD_STATUSES


def _followup_due_at(lead: InsuranceLead) -> datetime | None:
    due_at = getattr(lead, "followup_due_at", None)
    if due_at is None:
        return None
    return normalize_to_utc_naive(due_at)


def _reference_date(reference: datetime | None = None) -> date:
    return (reference or utcnow_naive()).date()


def is_upcoming_followup(lead: InsuranceLead, *, now: datetime | None = None) -> bool:
    """Open follow-ups scheduled today or later (calendar date)."""
    if not is_open_lead(lead):
        return False
    due = _followup_due_at(lead)
    if due is None:
        return False
    return due.date() >= _reference_date(now)


def is_followup_due_within_hours(
    lead: InsuranceLead,
    hours: int = FOLLOWUP_DUE_WINDOW_HOURS,
    *,
    now: datetime | None = None,
) -> bool:
    """Open follow-ups due today or within the next N hours."""
    if not is_open_lead(lead):
        return False
    due = _followup_due_at(lead)
    if due is None:
        return False
    reference = now or utcnow_naive()
    if due.date() == reference.date():
        return True
    window_end = reference + timedelta(hours=hours)
    return reference <= due <= window_end


def is_missed_followup(lead: InsuranceLead, *, now: datetime | None = None) -> bool:
    """Open follow-ups with a follow-up date before today."""
    if not is_open_lead(lead):
        return False
    due = _followup_due_at(lead)
    if due is None:
        return False
    return due.date() < _reference_date(now)


def classify_lead_followup_overview(leads: list[InsuranceLead]) -> dict[str, int]:
    now = utcnow_naive()
    return {
        "total_leads": len(leads),
        "upcoming_followups": sum(1 for lead in leads if is_upcoming_followup(lead, now=now)),
        "due_in_48_hours": sum(
            1 for lead in leads if is_followup_due_within_hours(lead, FOLLOWUP_DUE_WINDOW_HOURS, now=now)
        ),
        "missed_followups": sum(1 for lead in leads if is_missed_followup(lead, now=now)),
    }
