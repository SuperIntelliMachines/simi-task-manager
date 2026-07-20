"""Claims ReminderIntegrationService → SIMI ReminderConfigCreateBody adapter.

Claims calls POST /api/v1/reminders/config with a module-specific payload.
This adapter translates that shape into the native Reminder Engine create body
without changing Claims, Generator, Processor, or ReminderConfigService.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReminderAnchorType, ReminderOffsetDirection
from app.services.external_organization_mapping_service import (
    CLAIMS_SOURCE_SYSTEM,
    ExternalOrganizationMappingService,
)
from app.services.reminder_resolvers.claims_resolver import CLAIMS_ENTITY_TYPE

CLAIMS_EXTERNAL_ENTITY_TYPE = "crm_service_case"

# Claims channel keys → SIMI ChannelService keys
CLAIMS_CHANNEL_ALIASES: dict[str, str] = {
    "web": "in_app",
    "in_app": "in_app",
    "telegram": "telegram",
    "email": "email",
    "sms": "sms",
    "whatsapp": "whatsapp",
}

_OFFSET_UNITS = frozenset({"hours", "days", "weeks", "months"})


class ClaimsReminderConfigAdapterError(ValueError):
    """Raised when a Claims integration payload cannot be mapped to SIMI."""


def is_claims_integration_payload(data: dict[str, Any]) -> bool:
    """Return True when the request matches the Claims ReminderIntegration shape."""
    entity_type = str(data.get("entity_type") or "").strip().lower()
    if entity_type == CLAIMS_EXTERNAL_ENTITY_TYPE:
        return True

    # Shape detection: nested trigger + offset.amount/unit, without native SIMI fields.
    has_native_reminders = isinstance(data.get("reminders"), list)
    has_legacy = data.get("channel") is not None and data.get("offsets") is not None
    if has_native_reminders or has_legacy:
        return False

    trigger = data.get("trigger")
    offset = data.get("offset")
    has_claims_trigger = isinstance(trigger, dict)
    has_claims_offset = isinstance(offset, dict) and (
        "amount" in offset or "unit" in offset
    )
    return has_claims_trigger and has_claims_offset


def map_claims_channel(channel: object) -> str:
    raw = str(channel or "").strip().lower()
    if not raw:
        raise ClaimsReminderConfigAdapterError("channels entries must not be empty")
    mapped = CLAIMS_CHANNEL_ALIASES.get(raw)
    if mapped is None:
        raise ClaimsReminderConfigAdapterError(
            f"unsupported Claims channel '{raw}'; "
            f"supported aliases: {', '.join(sorted(CLAIMS_CHANNEL_ALIASES))}"
        )
    return mapped


def map_claims_channels(channels: object) -> list[str]:
    if not isinstance(channels, list) or not channels:
        raise ClaimsReminderConfigAdapterError(
            "Claims payload requires a non-empty channels array"
        )
    mapped = [map_claims_channel(item) for item in channels]
    # Preserve order, drop duplicates after aliasing (web + in_app → one in_app).
    deduped: list[str] = []
    seen: set[str] = set()
    for channel in mapped:
        if channel not in seen:
            seen.add(channel)
            deduped.append(channel)
    return deduped


def map_claims_entity_type(entity_type: object) -> str:
    normalized = str(entity_type or "").strip().lower()
    if not normalized:
        raise ClaimsReminderConfigAdapterError("entity_type must not be empty")
    if normalized in {CLAIMS_EXTERNAL_ENTITY_TYPE, CLAIMS_ENTITY_TYPE}:
        return CLAIMS_ENTITY_TYPE
    # Shape-detected Claims payloads with another entity_type still normalize to claims
    # only when they used crm_service_case; otherwise keep as provided for forward-compat.
    return normalized


def _coerce_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ClaimsReminderConfigAdapterError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    raise ClaimsReminderConfigAdapterError(
        f"{field_name} must be an integer (got {value!r})"
    )


def is_claims_tenant_uuid(value: object) -> bool:
    """Return True when value looks like a Claims tenant UUID string."""
    if not isinstance(value, str):
        return False
    raw = value.strip()
    if not raw:
        return False
    try:
        uuid.UUID(raw)
    except ValueError:
        return False
    return True


def _coerce_organization_id(
    value: object,
    *,
    resolved_organization_id: int | None = None,
) -> int:
    if resolved_organization_id is not None:
        return int(resolved_organization_id)
    if is_claims_tenant_uuid(value):
        raise ClaimsReminderConfigAdapterError(
            "Claims organization_id tenant UUID requires mapping resolution "
            "via external_organization_mappings"
        )
    return _coerce_positive_int(value, field_name="organization_id")


def _map_trigger(trigger: object) -> tuple[str, str, str]:
    """Return (anchor_type, anchor_key, offset_direction)."""
    if not isinstance(trigger, dict) or not trigger:
        raise ClaimsReminderConfigAdapterError(
            "Claims payload requires a trigger object"
        )

    to_status = str(trigger.get("to_status") or "").strip().lower()
    reminder_key = str(trigger.get("reminder_key") or "").strip()
    trigger_type = str(trigger.get("type") or "").strip().lower()

    # Workflow status keys (pending_submission, …) are the Claims resolver anchors.
    anchor_key = to_status or reminder_key or trigger_type
    if not anchor_key:
        raise ClaimsReminderConfigAdapterError(
            "Claims trigger requires to_status, reminder_key, or type"
        )

    # Claims integration events are workflow/status based (case_created, status change).
    if trigger_type in {ReminderAnchorType.DATE.value, ReminderAnchorType.WORKFLOW.value}:
        anchor_type = trigger_type
    else:
        anchor_type = ReminderAnchorType.WORKFLOW.value

    # Follow-ups after case/status events default to AFTER (Claims: amount days from event).
    explicit = str(trigger.get("offset_direction") or trigger.get("direction") or "").strip().lower()
    if explicit in {
        ReminderOffsetDirection.BEFORE.value,
        ReminderOffsetDirection.AFTER.value,
    }:
        offset_direction = explicit
    else:
        offset_direction = ReminderOffsetDirection.AFTER.value

    return anchor_type, anchor_key, offset_direction


def _map_offset(offset: object) -> tuple[int, str]:
    if not isinstance(offset, dict):
        raise ClaimsReminderConfigAdapterError(
            "Claims payload requires an offset object with amount and unit"
        )
    if "amount" not in offset:
        raise ClaimsReminderConfigAdapterError("Claims offset.amount is required")
    amount = _coerce_positive_int(offset.get("amount"), field_name="offset.amount")
    if amount < 0:
        raise ClaimsReminderConfigAdapterError("Claims offset.amount must be >= 0")

    unit = str(offset.get("unit") or "days").strip().lower()
    if unit not in _OFFSET_UNITS:
        raise ClaimsReminderConfigAdapterError(
            f"Claims offset.unit must be one of: {', '.join(sorted(_OFFSET_UNITS))}"
        )
    return amount, unit


def _map_recipients(recipients: object) -> list[dict[str, Any]]:
    """Map Claims recipients array into SIMI recipient_data list."""
    if recipients is None:
        return []
    if not isinstance(recipients, list):
        raise ClaimsReminderConfigAdapterError("Claims recipients must be an array")

    mapped_recipients: list[dict[str, Any]] = []
    for item in recipients:
        if not isinstance(item, dict):
            raise ClaimsReminderConfigAdapterError(
                "Claims recipients entries must be JSON objects"
            )
        entry = dict(item)
        # Normalize common Claims aliases onto SIMI channel address keys.
        alias_pairs = (
            ("recipient_user_id", "user_id"),
            ("simi_user_id", "user_id"),
            ("mobile", "phone"),
            ("whatsapp_number", "whatsapp"),
            ("telegram", "telegram_chat_id"),
        )
        for claims_key, simi_key in alias_pairs:
            if simi_key in entry and entry.get(simi_key) not in (None, ""):
                continue
            value = entry.get(claims_key)
            if value is None or value == "":
                continue
            entry[simi_key] = value
        mapped_recipients.append(entry)
    return mapped_recipients


def _map_template_variables(
    *,
    metadata: object,
    trigger: dict[str, Any],
    anchor_date: object,
) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ClaimsReminderConfigAdapterError("Claims metadata must be a JSON object")
        variables.update(metadata)

    if trigger.get("reminder_key") is not None:
        variables.setdefault("reminder_key", trigger.get("reminder_key"))
    if trigger.get("type") is not None:
        variables.setdefault("claims_trigger_type", trigger.get("type"))
    if trigger.get("to_status") is not None:
        variables.setdefault("to_status", trigger.get("to_status"))
    if anchor_date is not None:
        variables.setdefault("anchor_date", anchor_date)
    variables.setdefault("source", "claims_reminder_integration")
    return variables


def adapt_claims_reminder_config_payload(
    data: dict[str, Any],
    *,
    resolved_organization_id: int | None = None,
) -> dict[str, Any]:
    """
    Convert a Claims ReminderIntegration payload into native ReminderConfigCreateBody dict.

    Does not mutate the input dict.
    When Claims sends a tenant UUID as organization_id, pass the SIMI integer via
    ``resolved_organization_id`` (see ``adapt_claims_reminder_config_payload_async``).
    """
    if not is_claims_integration_payload(data):
        return data

    trigger = data.get("trigger")
    if not isinstance(trigger, dict):
        raise ClaimsReminderConfigAdapterError("Claims payload requires a trigger object")

    raw_organization_id = data.get("organization_id")
    organization_id = _coerce_organization_id(
        raw_organization_id,
        resolved_organization_id=resolved_organization_id,
    )
    entity_id = _coerce_positive_int(data.get("entity_id"), field_name="entity_id")
    entity_type = map_claims_entity_type(data.get("entity_type"))
    if str(data.get("entity_type") or "").strip().lower() == CLAIMS_EXTERNAL_ENTITY_TYPE:
        entity_type = CLAIMS_ENTITY_TYPE

    channels = map_claims_channels(data.get("channels"))
    offset_value, offset_unit = _map_offset(data.get("offset"))
    anchor_type, anchor_key, offset_direction = _map_trigger(trigger)

    template_raw = data.get("template")
    template_key = None
    if template_raw is not None:
        template_key = str(template_raw).strip() or None

    recipient_data = _map_recipients(data.get("recipients"))
    template_variables = _map_template_variables(
        metadata=data.get("metadata"),
        trigger=trigger,
        anchor_date=data.get("anchor_date"),
    )
    if is_claims_tenant_uuid(raw_organization_id):
        template_variables.setdefault(
            "claims_tenant_id", str(raw_organization_id).strip()
        )

    # Append per-case configs; do not wipe sibling rules Claims may have created.
    replace_existing = data.get("replace_existing")
    if replace_existing is None:
        replace_existing = False

    return {
        "organization_id": organization_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reminders": [
            {
                "channels": channels,
                "offset_value": offset_value,
                "offset_unit": offset_unit,
                "anchor_type": anchor_type,
                "anchor_key": anchor_key,
                "offset_direction": offset_direction,
            }
        ],
        "template_key": template_key,
        "template_variables": template_variables,
        "recipient_data": recipient_data,
        "entity_label": data.get("entity_label"),
        "sender_name": data.get("sender_name"),
        "replace_existing": bool(replace_existing),
    }


async def adapt_claims_reminder_config_payload_async(
    data: dict[str, Any],
    session: AsyncSession,
) -> dict[str, Any]:
    """Async Claims adapter that resolves tenant UUIDs via external_organization_mappings."""
    if not is_claims_integration_payload(data):
        return data

    resolved_organization_id: int | None = None
    raw_organization_id = data.get("organization_id")
    if is_claims_tenant_uuid(raw_organization_id):
        tenant_uuid = str(raw_organization_id).strip()
        mapped = await ExternalOrganizationMappingService(session).resolve_organization_id(
            source_system=CLAIMS_SOURCE_SYSTEM,
            external_id=tenant_uuid,
        )
        if mapped is None:
            raise ClaimsReminderConfigAdapterError(
                f"No SIMI organization mapped for Claims tenant '{tenant_uuid}'"
            )
        resolved_organization_id = mapped

    return adapt_claims_reminder_config_payload(
        data,
        resolved_organization_id=resolved_organization_id,
    )
