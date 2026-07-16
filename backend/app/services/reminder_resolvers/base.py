"""Entity resolver interface for generic reminder generation and delivery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.channel_keys import SUPPORTED_REMINDER_CHANNELS
from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    ReminderAnchorType,
    ReminderStopCondition,
)
from app.models.reminder_config import ReminderConfig
from app.services.reminder_resolvers.metadata import (
    ReminderModuleMetadata,
    ReminderRecipientType,
    ReminderTriggerField,
)
from app.utils.datetime_utils import normalize_to_utc_naive

REMINDER_DATETIME_FORMAT = "%d-%m-%Y %I:%M %p"

GENERIC_REMINDER_TEMPLATE = (
    "Hi {{name}}, this is a reminder regarding your pending {{entity_label}} "
    "({{reference_id}}). The due date is {{due_date}} ({{days_left}} days remaining). "
    "Please take the necessary action."
)


@dataclass(frozen=True)
class ReminderEntitySnapshot:
    """Module-neutral view of an entity used by the reminder scheduler and processor."""

    organization_id: int
    entity_type: str
    entity_id: int
    anchor_date: datetime | None
    recipient: str | None = None
    """Phone/email/chat recipient for outbound messaging channels."""
    recipient_user_id: int | None = None
    """SIMI user id for the in_app notification channel."""
    recipient_email: str | None = None
    """Optional email address for email-channel delivery."""
    reference_id: str = ""
    customer_name: str = "Customer"
    metadata: dict[str, Any] = field(default_factory=dict)
    """Module-specific diagnostic / delivery metadata."""
    source: Any = field(default=None, compare=False, repr=False)


class UnsupportedReminderEntityTypeError(KeyError):
    """Raised when no resolver is registered for an entity_type."""


def _lookup_datetime_on_source(source: Any, anchor_key: str) -> datetime | None:
    """Generic datetime lookup on an entity source (ORM object or dict)."""
    key = (anchor_key or "").strip()
    if not key:
        return None

    candidates = (
        key,
        f"{key}_at",
        f"{key}_on",
        f"entered_{key}_at",
        f"{key}_entered_at",
    )

    if isinstance(source, dict):
        for candidate in candidates:
            parsed = _coerce_datetime(source.get(candidate))
            if parsed is not None:
                return parsed
        for nested_key in ("timestamps", "lifecycle", "status_timestamps", "events"):
            nested = source.get(nested_key)
            if isinstance(nested, dict):
                nested_hit = _lookup_datetime_on_source(nested, key)
                if nested_hit is not None:
                    return nested_hit
        return None

    for candidate in candidates:
        if hasattr(source, candidate):
            parsed = _coerce_datetime(getattr(source, candidate, None))
            if parsed is not None:
                return parsed
    return None


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return normalize_to_utc_naive(value)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            return normalize_to_utc_naive(datetime.fromisoformat(text))
        except ValueError:
            return None
    return None


class ReminderEntityResolver(ABC):
    """Resolve entities and delivery context for a single module type."""

    entity_type: str

    @abstractmethod
    async def list_entities(
        self,
        session: AsyncSession,
        organization_id: int,
    ) -> list[ReminderEntitySnapshot]:
        """Return all entities in the organization that may receive reminders."""

    @abstractmethod
    async def get_entity(
        self,
        session: AsyncSession,
        organization_id: int,
        entity_id: int,
    ) -> ReminderEntitySnapshot | None:
        """Return a single entity snapshot, or None if not found."""

    def resolve_anchor(
        self,
        entity: ReminderEntitySnapshot,
        anchor_type: str,
        anchor_key: str,
    ) -> datetime | None:
        """
        Resolve the scheduling clock for ``entity`` from config anchor fields.

        Module resolvers should override this to map ``anchor_key`` onto the
        correct entity datetime. The base implementation is intentionally
        generic: default key → snapshot.anchor_date; otherwise look up the key
        on ``entity.source``.
        """
        _ = anchor_type  # available for module overrides (date vs workflow)
        key = (anchor_key or "").strip().lower() or DEFAULT_REMINDER_ANCHOR_KEY
        if key in {DEFAULT_REMINDER_ANCHOR_KEY, "anchor_date"}:
            return normalize_to_utc_naive(entity.anchor_date)
        return _lookup_datetime_on_source(entity.source, key)

    def get_anchor_date(self, entity: ReminderEntitySnapshot) -> datetime | None:
        """Backward-compatible primary snapshot clock (default date anchor)."""
        return self.resolve_anchor(
            entity,
            ReminderAnchorType.DATE.value,
            DEFAULT_REMINDER_ANCHOR_KEY,
        )

    def get_recipient(self, entity: ReminderEntitySnapshot) -> str | None:
        return entity.recipient

    def get_recipient_user_id(self, entity: ReminderEntitySnapshot) -> int | None:
        """Return the SIMI user id for in_app delivery, when available."""
        return entity.recipient_user_id

    def get_reference(self, entity: ReminderEntitySnapshot) -> str:
        return entity.reference_id

    def get_customer_name(self, entity: ReminderEntitySnapshot) -> str:
        return (entity.customer_name or "").strip() or "Customer"

    def get_default_entity_label(self) -> str:
        return (self.entity_type or "").strip().title() or "Reminder"

    def get_default_sender_name(self) -> str:
        return "SIMI"

    def metadata(self) -> ReminderModuleMetadata:
        """
        Publish Reminder Management capabilities for this module.

        New modules override this method; the Reminder UI renders whatever is returned
        and must not hardcode Insurance/Claims/etc. catalogs.
        """
        label = self.get_default_entity_label()
        return ReminderModuleMetadata(
            id=(self.entity_type or "").strip().lower(),
            name=label,
            trigger_types=(
                ReminderTriggerField(
                    key=DEFAULT_REMINDER_ANCHOR_KEY,
                    label="Anchor Date",
                    type="date",
                ),
            ),
            workflow_events=(),
            recipient_types=(ReminderRecipientType(id="customer", label="Customer"),),
            supported_channels=SUPPORTED_REMINDER_CHANNELS,
            default_template=None,
        )

    def get_whatsapp_template_spec(self) -> tuple[str | None, str | None]:
        """Return (template_name, language) when WhatsApp uses a Meta template."""
        return None, None

    def format_due_date(self, due_date: datetime | None) -> str:
        if due_date is None:
            return "-"
        return due_date.strftime("%d-%m-%Y")

    def format_reminder_date(self, scheduled_at: datetime) -> str:
        return scheduled_at.strftime(REMINDER_DATETIME_FORMAT)

    def build_template_context(
        self,
        entity: ReminderEntitySnapshot,
        *,
        entity_label: str,
        sender_name: str,
        scheduled_at: datetime,
    ) -> dict[str, str]:
        """Variables for WhatsApp templates and other channel payloads."""
        return {
            "customer_name": self.get_customer_name(entity),
            "entity_label": entity_label,
            "reminder_date": self.format_reminder_date(scheduled_at),
            "sender_name": sender_name,
        }

    def build_text_message(
        self,
        entity: ReminderEntitySnapshot,
        *,
        entity_label: str,
        scheduled_at: datetime,
        now: datetime,
    ) -> str:
        due_date = self.get_anchor_date(entity)
        due_date_label = self.format_due_date(due_date)
        days_left = self._days_left(due_date=due_date, now=now)
        return (
            GENERIC_REMINDER_TEMPLATE.replace("{{name}}", self.get_customer_name(entity))
            .replace("{{entity_label}}", entity_label)
            .replace("{{reference_id}}", self.get_reference(entity))
            .replace("{{due_date}}", due_date_label)
            .replace("{{days_left}}", str(days_left))
        )

    def should_cancel_instance(self, entity: ReminderEntitySnapshot) -> bool:
        """Return True when a pending instance should be canceled without sending."""
        return False

    def should_stop_reminder(
        self,
        entity: ReminderEntitySnapshot,
        config: ReminderConfig,
        *,
        sent_count: int,
        now: datetime,
    ) -> bool:
        """
        Return True when the configured stop condition is satisfied.

        Engine-level checks (config inactive, max_attempts) are handled separately.
        """
        stop = (
            getattr(config, "stop_condition", None) or ReminderStopCondition.ENTITY_INELIGIBLE.value
        ).strip().lower()
        if stop == ReminderStopCondition.NEVER.value:
            return False
        if stop == ReminderStopCondition.MAX_ATTEMPTS_REACHED.value:
            max_attempts = getattr(config, "max_attempts", None)
            return max_attempts is not None and int(sent_count) >= int(max_attempts)
        if stop == ReminderStopCondition.WORKFLOW_STATUS_CHANGED.value:
            return self.should_cancel_instance(entity)
        if stop == ReminderStopCondition.END_DATE_REACHED.value:
            return self._is_end_date_reached(entity, config, now=now)
        if stop == ReminderStopCondition.ENTITY_INELIGIBLE.value:
            if self.should_cancel_instance(entity):
                return True
            return not self.is_eligible(entity, configs=[config])
        return False

    def _is_end_date_reached(
        self,
        entity: ReminderEntitySnapshot,
        config: ReminderConfig,
        *,
        now: datetime,
    ) -> bool:
        raw_config = getattr(config, "stop_condition_config", None) or {}
        anchor_key = str(
            raw_config.get("end_date_anchor_key")
            or raw_config.get("anchor_key")
            or getattr(config, "anchor_key", DEFAULT_REMINDER_ANCHOR_KEY)
            or DEFAULT_REMINDER_ANCHOR_KEY
        ).strip()
        anchor_type = str(
            raw_config.get("anchor_type")
            or getattr(config, "anchor_type", ReminderAnchorType.DATE.value)
            or ReminderAnchorType.DATE.value
        ).strip()
        end_at = normalize_to_utc_naive(
            self.resolve_anchor(entity, anchor_type=anchor_type, anchor_key=anchor_key)
        )
        if end_at is None:
            return False
        return normalize_to_utc_naive(now) >= end_at

    def is_eligible(
        self,
        entity: ReminderEntitySnapshot,
        *,
        configs: list[ReminderConfig],
    ) -> bool:
        """Return True when at least one config can resolve a scheduling anchor."""
        if not configs:
            return False
        for config in configs:
            anchor = self.resolve_anchor(
                entity,
                getattr(config, "anchor_type", ReminderAnchorType.DATE.value)
                or ReminderAnchorType.DATE.value,
                getattr(config, "anchor_key", DEFAULT_REMINDER_ANCHOR_KEY)
                or DEFAULT_REMINDER_ANCHOR_KEY,
            )
            if normalize_to_utc_naive(anchor) is not None:
                return True
        return False

    def should_generate(
        self,
        entity: ReminderEntitySnapshot,
        *,
        configs: list[ReminderConfig],
    ) -> bool:
        """Backward-compatible alias for is_eligible."""
        return self.is_eligible(entity, configs=configs)

    def _days_left(self, *, due_date: datetime | None, now: datetime) -> int:
        if due_date is None:
            return 0
        return max(0, (due_date.date() - now.date()).days)
