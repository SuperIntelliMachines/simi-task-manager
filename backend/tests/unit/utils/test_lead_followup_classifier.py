from datetime import timedelta

from app.utils.datetime_utils import utcnow_naive
from app.utils.lead_followup_classifier import (
    classify_lead_followup_overview,
    is_followup_due_within_hours,
    is_missed_followup,
    is_upcoming_followup,
)


class _Lead:
    def __init__(self, *, status: str, followup_due_at=None):
        self.status = status
        self.followup_due_at = followup_due_at


def test_classify_lead_followup_overview():
    now = utcnow_naive()
    leads = [
        _Lead(status="follow_up_pending", followup_due_at=now + timedelta(hours=6)),
        _Lead(status="interested", followup_due_at=now + timedelta(days=3)),
        _Lead(status="follow_up_later", followup_due_at=now - timedelta(days=1)),
        _Lead(status="renewed", followup_due_at=now - timedelta(days=1)),
        _Lead(status="open", followup_due_at=None),
        _Lead(status="follow_up_pending", followup_due_at=now + timedelta(hours=30)),
    ]

    summary = classify_lead_followup_overview(leads)  # type: ignore[arg-type]

    assert summary["total_leads"] == 6
    assert summary["upcoming_followups"] == 3
    assert summary["due_in_48_hours"] == 2
    assert summary["missed_followups"] == 1


def test_today_followup_is_not_marked_missed_when_time_has_passed():
    now = utcnow_naive()
    today_morning = now.replace(hour=9, minute=0, second=0, microsecond=0)
    reference = now.replace(hour=16, minute=0, second=0, microsecond=0)
    lead = _Lead(status="follow_up_pending", followup_due_at=today_morning)

    assert is_upcoming_followup(lead, now=reference) is True
    assert is_missed_followup(lead, now=reference) is False
    assert is_followup_due_within_hours(lead, 48, now=reference) is True


def test_yesterday_followup_is_missed_not_upcoming():
    now = utcnow_naive()
    lead = _Lead(status="interested", followup_due_at=now - timedelta(days=1))

    assert is_missed_followup(lead, now=now) is True
    assert is_upcoming_followup(lead, now=now) is False
    assert is_followup_due_within_hours(lead, 48, now=now) is False
