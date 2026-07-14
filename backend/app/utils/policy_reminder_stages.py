"""Policy renewal reminder stages — generated dynamically by the daily scheduler."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.utils.datetime_utils import (
    expiry_ist_calendar_date,
    normalize_reminder_send_at,
    normalize_to_utc_naive,
    reminder_send_at_ist_date,
    utcnow_naive,
)

DEFAULT_REMINDER_OFFSETS: tuple[int, ...] = (30, 15, 10, 5, 2, 1, 0)

# Days remaining until expiry → reminder type
REMINDER_STAGE_TYPES: dict[int, str] = {
    30: "DUE_30_DAYS",
    15: "DUE_15_DAYS",
    10: "UPCOMING_10_DAYS",
    5: "UPCOMING_5_DAYS",
    2: "CRITICAL_2_DAYS",
    1: "CRITICAL_1_DAY",
    0: "EXPIRY_DAY",
}

REMINDER_DAYS_REMAINING: tuple[int, ...] = tuple(sorted(REMINDER_STAGE_TYPES.keys(), reverse=True))

RENEWAL_REMINDER_WINDOW_DAYS = 30
# Calendar months can be 31 days; allow generation slightly before the strict offset window.
REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS = 7
EXPIRY_DAY_REMINDER_TYPE = "EXPIRY_DAY"
ESCALATION_REMINDER_TYPE = "ESCALATION"
ESCALATION_DAYS_AFTER_EXPIRY = 1
PERSONALIZED_REMINDER_TYPE = "PERSONALIZED"
REMINDER_TYPE_DEFAULT = "default"
REMINDER_TYPE_PERSONALIZED = "personalized"

STAGE_DIRECTION_BEFORE = "BEFORE"
STAGE_DIRECTION_ON = "ON"
STAGE_DIRECTION_AFTER = "AFTER"


@dataclass(frozen=True)
class ReminderScheduleEntry:
    """One scheduled policy reminder row with stage metadata."""

    reminder_type: str
    stage: int
    stage_direction: str
    stage_unit: str
    stage_value: int
    reminder_at: datetime

    @property
    def stage_key(self) -> tuple[str, str, int]:
        """Unique stage identity beyond legacy ``stage`` integer."""
        return (self.stage_direction, self.stage_unit, self.stage_value)


def normalize_row_reminder_type(reminder_type: str | None) -> str:
    """Normalize policy_reminders.reminder_type for comparisons."""
    return (reminder_type or "").strip().upper()


def row_reminder_type_is_personalized(reminder_type: str | None) -> bool:
    """True for personalized schedule rows (PERSONALIZED / personalized)."""
    return normalize_row_reminder_type(reminder_type) == PERSONALIZED_REMINDER_TYPE


def row_reminder_type_is_escalation(reminder_type: str | None) -> bool:
    return normalize_row_reminder_type(reminder_type) == ESCALATION_REMINDER_TYPE


def row_reminder_type_is_expiry_day(reminder_type: str | None) -> bool:
    return normalize_row_reminder_type(reminder_type) == EXPIRY_DAY_REMINDER_TYPE


def row_stage_direction_is_after(stage_direction: str | None) -> bool:
    return (stage_direction or "").strip().upper() == STAGE_DIRECTION_AFTER


def row_stage_direction_is_before(stage_direction: str | None) -> bool:
    return (stage_direction or "").strip().upper() == STAGE_DIRECTION_BEFORE


def _reminder_field(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def days_remaining_until_expiry(expiry_date: datetime | None) -> int | None:
    if expiry_date is None:
        return None
    now = utcnow_naive()
    target = normalize_to_utc_naive(expiry_date)
    return (target.date() - now.date()).days


def reminder_type_for_days_remaining(days_remaining: int) -> str | None:
    return REMINDER_STAGE_TYPES.get(days_remaining)


def personalized_reminder_offset_days(unit: str | None, value: int | None) -> int | None:
    """Convert personalized unit/value into a single days-before-expiry offset."""
    if value is None or int(value) <= 0:
        return None

    normalized_unit = (unit or "days").strip().lower()
    amount = int(value)

    if normalized_unit == "days":
        return amount
    if normalized_unit == "weeks":
        return amount * 7
    if normalized_unit == "months":
        return amount * 30
    return None


def personalized_reminder_stage(unit: str | None, value: int | None) -> int | None:
    """Map a custom reminder config to a positive scheduler stage value."""
    metadata = personalized_reminder_metadata(unit, value)
    if metadata is None:
        return None
    return metadata[0]


def personalized_reminder_metadata(
    unit: str | None,
    value: int | None,
) -> tuple[int, str, str, int] | None:
    """
    Return (stage, stage_direction, stage_unit, stage_value) for a custom reminder.

    Stage is always positive; timeline position is expressed via stage_direction.
    """
    if value is None or int(value) <= 0:
        return None

    normalized_unit = (unit or "days").strip().lower()
    amount = int(value)

    if normalized_unit == "hours":
        return amount, STAGE_DIRECTION_BEFORE, "hours", amount

    offset_days = personalized_reminder_offset_days(normalized_unit, amount)
    if offset_days is None:
        return None
    return offset_days, STAGE_DIRECTION_BEFORE, normalized_unit, amount


def expiry_day_metadata() -> tuple[int, str, str, int]:
    return 0, STAGE_DIRECTION_ON, "day", 0


def escalation_metadata() -> tuple[int, str, str, int]:
    return 1, STAGE_DIRECTION_AFTER, "days", ESCALATION_DAYS_AFTER_EXPIRY


def default_offset_metadata(days_before: int) -> tuple[int, str, str, int]:
    if days_before == 0:
        return expiry_day_metadata()
    return days_before, STAGE_DIRECTION_BEFORE, "days", days_before


def get_policy_reminder_offsets(
    *,
    reminder_type: str | None,
    reminder_unit: str | None,
    reminder_value: int | None,
    custom_reminders: Sequence[Any] | None = None,
) -> list[int]:
    normalized = (reminder_type or REMINDER_TYPE_DEFAULT).strip().lower()
    if normalized == REMINDER_TYPE_PERSONALIZED:
        if custom_reminders:
            offsets: list[int] = []
            for item in custom_reminders:
                metadata = personalized_reminder_metadata(
                    _reminder_field(item, "reminder_unit"),
                    _reminder_field(item, "reminder_value"),
                )
                if metadata is None:
                    continue
                stage, direction, unit, _value = metadata
                if direction == STAGE_DIRECTION_BEFORE and unit != "hours":
                    offsets.append(stage)
            if offsets:
                return offsets
        offset = personalized_reminder_offset_days(reminder_unit, reminder_value)
        return [offset] if offset is not None else []
    return list(DEFAULT_REMINDER_OFFSETS)


def offset_matches_today(
    expiry_date: datetime | None,
    offset_days: int,
) -> bool:
    days_remaining = days_remaining_until_expiry(expiry_date)
    return days_remaining is not None and days_remaining == offset_days


def expiry_day_start(expiry_date: datetime) -> datetime:
    """Legacy UTC midnight on expiry date — prefer ``expiry_day_reminder_at`` for schedules."""
    normalized = normalize_to_utc_naive(expiry_date)
    assert normalized is not None
    return normalized.replace(hour=0, minute=0, second=0, microsecond=0)


def expiry_anchor_utc(expiry_date: datetime) -> datetime:
    """UTC-naive expiry instant (legacy anchor — schedules use IST-normalized send times)."""
    normalized = normalize_to_utc_naive(expiry_date)
    assert normalized is not None
    return normalized


def expiry_day_reminder_at(expiry_date: datetime) -> datetime:
    """09:00 IST on the policy expiry calendar date (UTC-naive)."""
    return reminder_send_at_ist_date(expiry_ist_calendar_date(expiry_date))


def scheduled_reminder_at(expiry_date: datetime, days_before_expiry: int) -> datetime:
    target_date = expiry_ist_calendar_date(expiry_date) - timedelta(days=days_before_expiry)
    return reminder_send_at_ist_date(target_date)


def scheduled_personalized_reminder_at(expiry_date: datetime, days_before_expiry: int) -> datetime:
    """Days-before-expiry on IST calendar, send at 09:00 IST (UTC-naive)."""
    return scheduled_reminder_at(expiry_date, days_before_expiry)


def scheduled_custom_reminder_at(
    expiry_date: datetime,
    *,
    unit: str | None,
    value: int | None,
) -> datetime:
    """
    Compute personalized reminder send time from the original policy expiry only.

    Each configured offset is applied independently; earlier schedule entries must
    not shift the anchor used for later ones.
    """
    if value is None or int(value) <= 0:
        raise ValueError("reminder value must be positive")

    normalized_unit = (unit or "days").strip().lower()
    amount = int(value)
    if normalized_unit == "hours":
        return scheduled_reminder_at_hours_before(expiry_date, amount)

    offset_days = personalized_reminder_offset_days(normalized_unit, amount)
    if offset_days is None:
        raise ValueError(f"unsupported reminder unit: {unit!r}")
    return scheduled_reminder_at(expiry_date, offset_days)


def scheduled_reminder_at_hours_before(expiry_date: datetime, hours_before_expiry: int) -> datetime:
    normalized = normalize_to_utc_naive(expiry_date)
    assert normalized is not None
    raw = normalized - timedelta(hours=hours_before_expiry)
    return normalize_reminder_send_at(raw)


def escalation_reminder_at(expiry_date: datetime) -> datetime:
    target_date = expiry_ist_calendar_date(expiry_date) + timedelta(days=ESCALATION_DAYS_AFTER_EXPIRY)
    return reminder_send_at_ist_date(target_date)


def personalized_escalation_reminder_at(expiry_date: datetime) -> datetime:
    return escalation_reminder_at(expiry_date)


def _schedule_entry(
    reminder_type: str,
    metadata: tuple[int, str, str, int],
    reminder_at: datetime,
) -> ReminderScheduleEntry:
    stage, stage_direction, stage_unit, stage_value = metadata
    return ReminderScheduleEntry(
        reminder_type=reminder_type,
        stage=stage,
        stage_direction=stage_direction,
        stage_unit=stage_unit,
        stage_value=stage_value,
        reminder_at=reminder_at,
    )


def build_renewal_reminder_schedule(expiry_date: datetime) -> list[ReminderScheduleEntry]:
    """Return default renewal schedule entries."""
    schedule: list[ReminderScheduleEntry] = []
    for days_before, reminder_type in sorted(REMINDER_STAGE_TYPES.items(), reverse=True):
        schedule.append(
            _schedule_entry(
                reminder_type,
                default_offset_metadata(days_before),
                scheduled_reminder_at(expiry_date, days_before),
            )
        )
    schedule.append(
        _schedule_entry(
            ESCALATION_REMINDER_TYPE,
            escalation_metadata(),
            escalation_reminder_at(expiry_date),
        )
    )
    return schedule


def build_personalized_reminder_schedule(
    expiry_date: datetime,
    *,
    unit: str,
    value: int,
) -> list[ReminderScheduleEntry]:
    """Return personalized reminder rows for the configured offset plus escalation only."""
    metadata = personalized_reminder_metadata(unit, value)
    if metadata is None:
        return []

    schedule: list[ReminderScheduleEntry] = []
    stage, direction, stage_unit, stage_value = metadata
    if direction == STAGE_DIRECTION_BEFORE:
        schedule.append(
            _schedule_entry(
                PERSONALIZED_REMINDER_TYPE,
                metadata,
                scheduled_custom_reminder_at(
                    expiry_date,
                    unit=stage_unit,
                    value=stage_value,
                ),
            )
        )

    schedule.append(
        _schedule_entry(
            ESCALATION_REMINDER_TYPE,
            escalation_metadata(),
            personalized_escalation_reminder_at(expiry_date),
        )
    )
    return schedule


def build_multi_custom_reminder_schedule(
    expiry_date: datetime,
    custom_reminders: Sequence[Any],
) -> list[ReminderScheduleEntry]:
    """Build personalized schedule rows from multiple custom reminder configs."""
    schedule: list[ReminderScheduleEntry] = []
    seen_keys: set[tuple[str, str, int]] = set()
    original_expiry = expiry_date

    for item in custom_reminders:
        unit = _reminder_field(item, "reminder_unit")
        value = _reminder_field(item, "reminder_value")
        metadata = personalized_reminder_metadata(unit, value)
        if metadata is None:
            continue
        stage_key = metadata[1:]  # direction, unit, value
        if stage_key in seen_keys:
            continue
        seen_keys.add(stage_key)

        _stage, _direction, stage_unit, stage_value = metadata
        reminder_at = scheduled_custom_reminder_at(
            original_expiry,
            unit=stage_unit,
            value=stage_value,
        )
        schedule.append(
            _schedule_entry(PERSONALIZED_REMINDER_TYPE, metadata, reminder_at)
        )

    schedule.append(
        _schedule_entry(
            ESCALATION_REMINDER_TYPE,
            escalation_metadata(),
            personalized_escalation_reminder_at(expiry_date),
        )
    )
    return schedule


def build_policy_reminder_schedule(
    expiry_date: datetime,
    *,
    reminder_type: str | None,
    reminder_unit: str | None,
    reminder_value: int | None,
    custom_reminders: Sequence[Any] | None = None,
) -> list[ReminderScheduleEntry]:
    normalized = (reminder_type or REMINDER_TYPE_DEFAULT).strip().lower()
    if normalized == REMINDER_TYPE_PERSONALIZED:
        if custom_reminders:
            return build_multi_custom_reminder_schedule(expiry_date, custom_reminders)
        if reminder_unit and reminder_value:
            return build_personalized_reminder_schedule(
                expiry_date,
                unit=reminder_unit,
                value=int(reminder_value),
            )
    return build_renewal_reminder_schedule(expiry_date)


def is_renewed_policy_status(status: str | None) -> bool:
    return (status or "").strip().lower() == "renewed"


def is_active_for_reminders(*, status: str | None, expiry_date: datetime | None) -> bool:
    if is_renewed_policy_status(status):
        return False
    days = days_remaining_until_expiry(expiry_date)
    if days is None:
        return False
    return days >= 0


def max_reminder_lookahead_days(
    *,
    reminder_type: str | None,
    reminder_unit: str | None,
    reminder_value: int | None,
    custom_reminders: Sequence[Any] | None = None,
) -> int:
    """Furthest days-before-expiry offset that should trigger schedule generation."""
    max_window = RENEWAL_REMINDER_WINDOW_DAYS
    normalized = (reminder_type or REMINDER_TYPE_DEFAULT).strip().lower()
    if normalized == REMINDER_TYPE_PERSONALIZED:
        if custom_reminders:
            for item in custom_reminders:
                metadata = personalized_reminder_metadata(
                    _reminder_field(item, "reminder_unit"),
                    _reminder_field(item, "reminder_value"),
                )
                if metadata is None:
                    continue
                stage, direction, unit, _value = metadata
                if direction == STAGE_DIRECTION_BEFORE and unit != "hours":
                    max_window = max(max_window, stage)
        else:
            offset = personalized_reminder_offset_days(reminder_unit, reminder_value)
            if offset is not None:
                max_window = max(max_window, offset)
    return max_window


def is_eligible_for_reminder_schedule(
    *,
    status: str | None,
    expiry_date: datetime | None,
    reminder_type: str | None = None,
    reminder_unit: str | None = None,
    reminder_value: int | None = None,
    custom_reminders: Sequence[Any] | None = None,
) -> bool:
    """Policies within the renewal reminder window (and not yet renewed)."""
    if is_renewed_policy_status(status):
        return False
    days = days_remaining_until_expiry(expiry_date)
    if days is None or days < 0:
        return False

    max_window = max_reminder_lookahead_days(
        reminder_type=reminder_type,
        reminder_unit=reminder_unit,
        reminder_value=reminder_value,
        custom_reminders=custom_reminders,
    )
    return days <= max_window + REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS
