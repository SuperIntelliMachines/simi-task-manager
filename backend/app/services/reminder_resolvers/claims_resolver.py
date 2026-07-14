"""Claims (Gyantr AI Service Case) entity resolver for the Generic Reminder Engine.

SIMI does NOT own or store Service Cases. This resolver fetches cases live via
ClaimsClient and maps them into ReminderEntitySnapshot.

Workflow anchors are resolved generically from ``anchor_key`` → case datetime
fields (e.g. pending_submission → pending_submission_at). No Claims business
rules live in ReminderGeneratorService.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.channel_keys import SUPPORTED_REMINDER_CHANNELS
from app.core.enums import DEFAULT_REMINDER_ANCHOR_KEY, ReminderAnchorType
from app.integrations.claims.client import ClaimsClient
from app.integrations.claims.exceptions import (
    ClaimsAuthenticationError,
    ClaimsIntegrationError,
    ClaimsNotFoundError,
)
from app.models.reminder_config import ReminderConfig
from app.services.reminder_resolvers.base import (
    ReminderEntitySnapshot,
    ReminderEntityResolver,
    _coerce_datetime,
    _lookup_datetime_on_source,
)
from app.services.reminder_resolvers.metadata import (
    ReminderModuleMetadata,
    ReminderRecipientType,
    ReminderTriggerField,
    ReminderWorkflowEvent,
)
from app.services.reminder_resolvers.registry import register_resolver

logger = logging.getLogger(__name__)

CLAIMS_ENTITY_TYPE = "claims"
DEFAULT_CLAIMS_ENTITY_LABEL = "Service Case"
DEFAULT_CLAIMS_SENDER_NAME = "SIMI Claims"
DEFAULT_LIST_PAGE_SIZE = 100
MAX_LIST_PAGES = 100

# Status values treated as non-eligible for reminder discovery sweeps.
_SKIP_STATUSES = frozenset(
    {
        "deleted",
        "cancelled",
        "canceled",
        "void",
        "archived",
    }
)

# Optional aliases → preferred payload field names.
# Lookups still fall through to generic ``{key}_at`` / nested timestamp maps.
_CLAIMS_ANCHOR_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    DEFAULT_REMINDER_ANCHOR_KEY: (
        "submitted_at",
        "status_changed_at",
        "lifecycle_at",
        "anchor_at",
        "due_at",
        "created_at",
    ),
    "anchor_date": (
        "submitted_at",
        "status_changed_at",
        "lifecycle_at",
        "anchor_at",
        "due_at",
        "created_at",
    ),
    "pending_submission": (
        "pending_submission_at",
        "entered_pending_submission_at",
        "pending_submission",
    ),
    "return_pending": (
        "return_pending_at",
        "entered_return_pending_at",
        "return_pending",
    ),
    "submitted": ("submitted_at", "submitted"),
    "approved": ("approved_at", "approved"),
}


@register_resolver(CLAIMS_ENTITY_TYPE)
class ClaimsReminderResolver(ReminderEntityResolver):
    """Resolve Claims Service Cases into the generic reminder entity format."""

    entity_type = CLAIMS_ENTITY_TYPE

    def __init__(self, client: ClaimsClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> ClaimsClient:
        if self._client is None:
            self._client = ClaimsClient()
        return self._client

    async def list_entities(
        self,
        session: AsyncSession,
        organization_id: int,
    ) -> list[ReminderEntitySnapshot]:
        """
        List Service Cases for reminder discovery via ClaimsClient.

        Fetches all pages from ``list_service_cases`` / ``list_all_service_cases``,
        maps each valid case through ``_to_snapshot``, and skips deleted/invalid rows.
        """
        _ = session
        logger.info(
            "Listing Claims service cases for reminder discovery organization_id=%s",
            organization_id,
        )

        try:
            # Tenant scope is determined by the Claims JWT/service account.
            # SIMI organization_id is applied only when building snapshots below.
            cases = await self.client.list_all_service_cases(
                page_size=DEFAULT_LIST_PAGE_SIZE,
                max_pages=MAX_LIST_PAGES,
            )
        except ClaimsAuthenticationError:
            logger.error(
                "Claims authentication failed while listing cases for organization_id=%s",
                organization_id,
            )
            raise
        except ClaimsIntegrationError:
            logger.error(
                "Claims API unavailable while listing cases for organization_id=%s",
                organization_id,
            )
            raise

        snapshots: list[ReminderEntitySnapshot] = []
        skipped = 0
        for case in cases:
            if self._should_skip_case(case):
                skipped += 1
                continue
            try:
                snapshots.append(self._to_snapshot(organization_id=organization_id, case=case))
            except ValueError as exc:
                skipped += 1
                logger.warning(
                    "Skipping invalid Claims service case during list_entities: %s",
                    exc,
                )

        logger.info(
            "Claims list_entities organization_id=%s fetched=%s mapped=%s skipped=%s",
            organization_id,
            len(cases),
            len(snapshots),
            skipped,
        )
        return snapshots

    async def get_entity(
        self,
        session: AsyncSession,
        organization_id: int,
        entity_id: int,
    ) -> ReminderEntitySnapshot | None:
        """Fetch one Service Case from Gyantr AI and map it to a snapshot."""
        _ = session
        try:
            case = await self.resolve_case(entity_id)
        except ClaimsNotFoundError:
            logger.info("Claims service case %s not found", entity_id)
            return None
        except ClaimsAuthenticationError:
            logger.error("Claims authentication failed while resolving case %s", entity_id)
            raise
        except ClaimsIntegrationError:
            logger.error("Claims API unavailable while resolving case %s", entity_id)
            raise

        if self._should_skip_case(case):
            logger.info("Claims service case %s skipped (deleted/invalid status)", entity_id)
            return None

        return self._to_snapshot(organization_id=organization_id, case=case)

    async def resolve_case(self, case_id: int | str) -> dict[str, Any]:
        """
        Fetch a Service Case from Gyantr AI via ClaimsClient.

        Raises:
            ClaimsNotFoundError: case does not exist
            ClaimsAuthenticationError: JWT auth failed
            ClaimsIntegrationError: network/timeout/API failures
        """
        logger.info("Resolving Claims service case %s via ClaimsClient", case_id)
        payload = await self.client.get_service_case(case_id)
        if not isinstance(payload, dict):
            raise ClaimsNotFoundError(f"Claims service case {case_id} returned an unexpected payload.")
        return payload

    def resolve_recipient(self, case: dict[str, Any]) -> str | None:
        """Extract the reminder recipient (phone) from a Service Case payload."""
        for key in (
            "customer_phone",
            "mobile_number",
            "phone",
            "phone_number",
            "contact_phone",
            "recipient",
        ):
            value = case.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        contact = case.get("contact")
        if isinstance(contact, dict):
            for key in ("phone", "mobile", "mobile_number", "phone_number"):
                value = contact.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        logger.debug("Claims service case missing recipient contact fields")
        return None

    def resolve_recipient_email(self, case: dict[str, Any]) -> str | None:
        """Extract an email recipient when present on the Service Case payload."""
        for key in ("customer_email", "email", "contact_email", "recipient_email"):
            value = case.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        contact = case.get("contact")
        if isinstance(contact, dict):
            value = contact.get("email")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def resolve_recipient_user_id(self, case: dict[str, Any]) -> int | None:
        """Extract a SIMI user id for in_app delivery when Claims provides one."""
        for key in (
            "recipient_user_id",
            "simi_user_id",
            "assigned_user_id",
            "owner_user_id",
            "user_id",
        ):
            value = case.get(key)
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, str) and value.strip().isdigit():
                parsed = int(value.strip())
                if parsed > 0:
                    return parsed

        assignee = case.get("assignee")
        if isinstance(assignee, dict):
            value = assignee.get("user_id") or assignee.get("id")
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, str) and value.strip().isdigit():
                parsed = int(value.strip())
                if parsed > 0:
                    return parsed
        return None

    def resolve_case_anchor(self, case: dict[str, Any]) -> datetime | None:
        """Resolve the default snapshot clock from a raw Service Case payload."""
        for key in _CLAIMS_ANCHOR_FIELD_ALIASES.get(DEFAULT_REMINDER_ANCHOR_KEY, ()):
            parsed = _coerce_datetime(case.get(key))
            if parsed is not None:
                if key == "created_at":
                    logger.debug(
                        "ClaimsReminderResolver.resolve_case_anchor using created_at fallback"
                    )
                return parsed
        logger.debug("Claims service case missing lifecycle/anchor fields")
        return None

    def resolve_anchor(
        self,
        entity: ReminderEntitySnapshot,
        anchor_type: str,
        anchor_key: str,
    ) -> datetime | None:
        """
        Map ``anchor_key`` to a Service Case datetime.

        Supports workflow keys such as pending_submission / return_pending /
        submitted / approved, plus any future key via generic field lookup.
        """
        case = entity.source if isinstance(entity.source, dict) else {}
        key = (anchor_key or "").strip().lower() or DEFAULT_REMINDER_ANCHOR_KEY

        preferred_fields = _CLAIMS_ANCHOR_FIELD_ALIASES.get(key)
        if preferred_fields:
            for field_name in preferred_fields:
                parsed = _coerce_datetime(case.get(field_name))
                if parsed is not None:
                    return parsed

        # Generic fallback: key / key_at / nested timestamp maps.
        looked_up = _lookup_datetime_on_source(case, key)
        if looked_up is not None:
            return looked_up

        # Default date-style configs may still use the snapshot clock.
        if key in {DEFAULT_REMINDER_ANCHOR_KEY, "anchor_date"} or (
            (anchor_type or "").strip().lower() == ReminderAnchorType.DATE.value
            and key in {DEFAULT_REMINDER_ANCHOR_KEY, "anchor_date"}
        ):
            return _coerce_datetime(entity.anchor_date)

        return None

    def resolve_metadata(self, case: dict[str, Any]) -> dict[str, Any]:
        """Collect metadata useful for diagnostics and future Claims rules."""
        return {
            "case_id": case.get("id") if case.get("id") is not None else case.get("case_id"),
            "status": case.get("status"),
            "title": case.get("title") or case.get("summary"),
            "reference": self._resolve_reference(case),
            "customer_name": self._resolve_customer_name(case),
            "recipient_email": self.resolve_recipient_email(case),
            "available_anchor_keys": sorted(
                {
                    key
                    for key, fields in _CLAIMS_ANCHOR_FIELD_ALIASES.items()
                    if any(_coerce_datetime(case.get(field)) is not None for field in fields)
                }
            ),
        }

    def get_default_entity_label(self) -> str:
        return DEFAULT_CLAIMS_ENTITY_LABEL

    def get_default_sender_name(self) -> str:
        return DEFAULT_CLAIMS_SENDER_NAME

    def metadata(self) -> ReminderModuleMetadata:
        return ReminderModuleMetadata(
            id=self.entity_type,
            name="Claims",
            # Claims scheduling is primarily stage-based; date fields still exist for
            # relative offsets after submitted_at / status_changed_at when present.
            trigger_types=(
                ReminderTriggerField(key="submitted_at", label="Submitted Date", type="date"),
                ReminderTriggerField(key="status_changed_at", label="Status Changed", type="date"),
            ),
            workflow_events=(
                ReminderWorkflowEvent(key="pending_submission", label="Pending Submission"),
                ReminderWorkflowEvent(key="return_pending", label="Return Pending"),
                ReminderWorkflowEvent(key="submitted", label="Submitted"),
                ReminderWorkflowEvent(key="approved", label="Approved"),
                ReminderWorkflowEvent(key="pending_approval", label="Pending Approval"),
            ),
            recipient_types=(
                ReminderRecipientType(id="assignee", label="Assignee"),
                ReminderRecipientType(id="reviewer", label="Reviewer"),
                ReminderRecipientType(id="owner", label="Owner"),
                ReminderRecipientType(id="customer", label="Customer"),
                ReminderRecipientType(id="store_staff", label="Store Staff"),
                ReminderRecipientType(id="store_manager", label="Store Manager"),
                ReminderRecipientType(id="md", label="MD"),
            ),
            supported_channels=SUPPORTED_REMINDER_CHANNELS,
            default_template="claims_workflow_reminder",
        )

    def is_eligible(
        self,
        entity: ReminderEntitySnapshot,
        *,
        configs: list[ReminderConfig],
    ) -> bool:
        """Eligible when at least one config's anchor_key resolves on the case."""
        return super().is_eligible(entity, configs=configs)

    def _should_skip_case(self, case: dict[str, Any]) -> bool:
        """Return True for deleted/invalid Service Cases that must not generate reminders."""
        if not isinstance(case, dict) or not case:
            return True

        if case.get("is_deleted") is True or case.get("deleted") is True:
            return True
        if case.get("deleted_at") not in (None, "", False):
            return True

        status = case.get("status")
        if isinstance(status, str) and status.strip().lower() in _SKIP_STATUSES:
            return True

        try:
            _coerce_entity_id(case)
        except ValueError:
            return True
        return False

    def _to_snapshot(self, *, organization_id: int, case: dict[str, Any]) -> ReminderEntitySnapshot:
        entity_id = _coerce_entity_id(case)
        return ReminderEntitySnapshot(
            organization_id=int(organization_id),
            entity_type=self.entity_type,
            entity_id=entity_id,
            anchor_date=self.resolve_case_anchor(case),
            recipient=self.resolve_recipient(case),
            recipient_user_id=self.resolve_recipient_user_id(case),
            recipient_email=self.resolve_recipient_email(case),
            reference_id=self._resolve_reference(case),
            customer_name=self._resolve_customer_name(case),
            metadata=self.resolve_metadata(case),
            source=case,
        )

    def _resolve_reference(self, case: dict[str, Any]) -> str:
        for key in ("case_number", "reference_id", "reference", "external_id", "id", "case_id"):
            value = case.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def _resolve_customer_name(self, case: dict[str, Any]) -> str:
        for key in ("customer_name", "contact_name", "name"):
            value = case.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        contact = case.get("contact")
        if isinstance(contact, dict):
            name = contact.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return "Customer"


def _coerce_entity_id(case: dict[str, Any]) -> int:
    for key in ("id", "case_id"):
        value = case.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    raise ValueError("Claims service case is missing a numeric id/case_id required by the reminder engine")
