"""Safe PolicyResponse serialization for async SQLAlchemy sessions."""

from __future__ import annotations

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.base import NEVER_SET, NO_VALUE

from app.models.verticals import InsurancePolicy
from app.schemas.custom_reminder_fields import CustomReminderSchema
from app.schemas.insurance import PolicyResponse

_POLICY_RESPONSE_EXTRAS = (
    "policyholder_name",
    "mobile",
    "email",
    "mobile_number",
    "currency",
)


def materialized_custom_reminders(policy: InsurancePolicy) -> list:
    """Return custom reminders only if already eager-loaded (never trigger lazy IO)."""
    attr_state = sa_inspect(policy).attrs.custom_reminders
    loaded = attr_state.loaded_value
    if loaded in (NO_VALUE, NEVER_SET):
        return []
    return list(loaded or [])


def policy_response_from_model(policy: InsurancePolicy) -> PolicyResponse:
    """Build PolicyResponse without async lazy-load on custom_reminders."""
    mapper = sa_inspect(InsurancePolicy)
    payload: dict[str, object] = {
        column.key: getattr(policy, column.key)
        for column in mapper.columns
    }
    for extra in _POLICY_RESPONSE_EXTRAS:
        if hasattr(policy, extra):
            payload[extra] = getattr(policy, extra)

    payload["custom_reminders"] = [
        CustomReminderSchema.model_validate(item)
        for item in materialized_custom_reminders(policy)
    ]
    return PolicyResponse.model_validate(payload)
