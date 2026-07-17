"""Policy (insurance renewal) entity resolver."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.channel_keys import SUPPORTED_REMINDER_CHANNELS
from app.channels.whatsapp_template_specs import (
    POLICY_RENEWAL_REMINDER_LANGUAGE,
    POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
)
from app.core.enums import DEFAULT_REMINDER_ANCHOR_KEY
from app.models.core import Contact
from app.models.reminder_config import ReminderConfig
from app.models.verticals import InsurancePolicy
from app.services.policy_reminder_messages import format_policy_renewal_date
from app.services.reminder_resolvers.base import (
    ReminderEntitySnapshot,
    ReminderEntityResolver,
    _lookup_datetime_on_source,
)
from app.services.reminder_resolvers.metadata import (
    ReminderModuleMetadata,
    ReminderRecipientType,
    ReminderTriggerField,
    ReminderWorkflowEvent,
)
from app.services.reminder_resolvers.registry import register_resolver
from app.utils.datetime_utils import normalize_to_utc_naive
from app.utils.policy_reminder_stages import (
    REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS,
    days_remaining_until_expiry,
    is_eligible_for_reminder_schedule,
)

POLICY_ENTITY_TYPE = "policy"
DEFAULT_POLICY_ENTITY_LABEL = "Policy Renewal"
DEFAULT_POLICY_SENDER_NAME = "SIMI Insurance"

# Map generic / Insurance-facing keys onto InsurancePolicy datetime attributes.
# renewal_date aliases expiry_date because Insurance treats expiry as the renewal clock.
_POLICY_DATE_FIELD_ALIASES: dict[str, str] = {
    DEFAULT_REMINDER_ANCHOR_KEY: "expiry_date",
    "anchor_date": "expiry_date",
    "expiry_date": "expiry_date",
    "renewal_date": "expiry_date",
}


@register_resolver(POLICY_ENTITY_TYPE)
class PolicyReminderResolver(ReminderEntityResolver):
    entity_type = POLICY_ENTITY_TYPE

    async def list_entities(
        self,
        session: AsyncSession,
        organization_id: int,
    ) -> list[ReminderEntitySnapshot]:
        result = await session.execute(
            select(InsurancePolicy).where(InsurancePolicy.organization_id == organization_id)
        )
        snapshots: list[ReminderEntitySnapshot] = []
        for policy in result.scalars():
            snapshot = await self._to_snapshot(session, policy)
            snapshots.append(snapshot)
        return snapshots

    async def get_entity(
        self,
        session: AsyncSession,
        organization_id: int,
        entity_id: int,
    ) -> ReminderEntitySnapshot | None:
        policy = await session.get(InsurancePolicy, entity_id)
        if policy is None or int(policy.organization_id) != int(organization_id):
            return None
        return await self._to_snapshot(session, policy)

    def resolve_anchor(
        self,
        entity: ReminderEntitySnapshot,
        anchor_type: str,
        anchor_key: str,
    ) -> datetime | None:
        """Translate ``anchor_key`` into an InsurancePolicy datetime."""
        _ = anchor_type
        key = (anchor_key or "").strip().lower() or DEFAULT_REMINDER_ANCHOR_KEY
        policy = entity.source
        if policy is None:
            if key in _POLICY_DATE_FIELD_ALIASES:
                return normalize_to_utc_naive(entity.anchor_date)
            return None

        attr_name = _POLICY_DATE_FIELD_ALIASES.get(key, key)
        if hasattr(policy, attr_name):
            return normalize_to_utc_naive(getattr(policy, attr_name, None))

        # Future date fields on the policy (or nested source) without hardcoding.
        return _lookup_datetime_on_source(policy, key)

    def get_default_entity_label(self) -> str:
        return DEFAULT_POLICY_ENTITY_LABEL

    def get_default_sender_name(self) -> str:
        return DEFAULT_POLICY_SENDER_NAME

    def metadata(self) -> ReminderModuleMetadata:
        return ReminderModuleMetadata(
            id=self.entity_type,
            name="Insurance",
            trigger_types=(
                ReminderTriggerField(key="expiry_date", label="Policy Expiry Date", type="date"),
                ReminderTriggerField(key="renewal_date", label="Renewal Date", type="date"),
            ),
            workflow_events=(
                ReminderWorkflowEvent(key="renewal_submitted", label="Renewal Submitted"),
            ),
            recipient_types=(
                ReminderRecipientType(id="customer", label="Customer"),
                ReminderRecipientType(id="assignee", label="Assignee"),
                ReminderRecipientType(id="manager", label="Manager"),
            ),
            supported_channels=SUPPORTED_REMINDER_CHANNELS,
            default_template=POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
        )

    def get_whatsapp_template_spec(self) -> tuple[str | None, str | None]:
        return POLICY_RENEWAL_REMINDER_TEMPLATE_NAME, POLICY_RENEWAL_REMINDER_LANGUAGE

    def format_due_date(self, due_date: datetime | None) -> str:
        return format_policy_renewal_date(due_date)

    def should_cancel_instance(self, entity: ReminderEntitySnapshot) -> bool:
        policy = entity.source
        if policy is None:
            return False
        return (policy.status or "").strip().lower() == "renewed"

    def is_eligible(
        self,
        entity: ReminderEntitySnapshot,
        *,
        configs: list[ReminderConfig],
    ) -> bool:
        if not super().is_eligible(entity, configs=configs):
            return False

        policy = entity.source
        if policy is None:
            return False
        if (policy.status or "").strip().lower() == "renewed":
            return False

        # Primary Insurance eligibility clock remains expiry/renewal.
        anchor = normalize_to_utc_naive(policy.expiry_date) or normalize_to_utc_naive(
            entity.anchor_date
        )
        if anchor is None:
            return False

        custom_reminders = list(getattr(policy, "custom_reminders", None) or [])
        if not is_eligible_for_reminder_schedule(
            status=policy.status,
            expiry_date=policy.expiry_date,
            reminder_type=getattr(policy, "reminder_type", None),
            reminder_unit=getattr(policy, "reminder_unit", None),
            reminder_value=getattr(policy, "reminder_value", None),
            custom_reminders=custom_reminders or None,
        ):
            max_offset = max(config.offset_value for config in configs)
            days = days_remaining_until_expiry(anchor)
            if days is None or days > max_offset + REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS:
                return False

        return True

    async def _to_snapshot(self, session: AsyncSession, policy: InsurancePolicy) -> ReminderEntitySnapshot:
        contact = await session.get(Contact, policy.policyholder_id)
        customer_name = (contact.name if contact is not None else None) or "Customer"
        phone = (policy.mobile_number or "").strip() or None
        # In-app notifications target the assigned Insurance agent (same as
        # insurance_service / escalation jobs). Phone channels use ``recipient``.
        assigned_agent_id = getattr(policy, "assigned_agent_user_id", None)
        recipient_user_id = (
            int(assigned_agent_id)
            if assigned_agent_id is not None and int(assigned_agent_id) > 0
            else None
        )
        return ReminderEntitySnapshot(
            organization_id=int(policy.organization_id),
            entity_type=self.entity_type,
            entity_id=int(policy.id),
            anchor_date=normalize_to_utc_naive(policy.expiry_date),
            recipient=phone,
            recipient_user_id=recipient_user_id,
            reference_id=(policy.policy_number or "").strip(),
            customer_name=customer_name,
            source=policy,
        )

    def get_recipient_user_id(self, entity: ReminderEntitySnapshot) -> int | None:
        if entity.recipient_user_id is not None and int(entity.recipient_user_id) > 0:
            return int(entity.recipient_user_id)
        policy = entity.source
        assigned = getattr(policy, "assigned_agent_user_id", None) if policy is not None else None
        if assigned is not None and int(assigned) > 0:
            return int(assigned)
        return None
