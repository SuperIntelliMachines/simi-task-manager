"""Lightweight reminder template catalog for Reminder Management metadata.

Placeholder until a durable template store / Message Templates CRM is wired in.
Resolvers can contribute default templates via ``metadata().default_template``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.channels.whatsapp_template_specs import (
    POLICY_RENEWAL_REMINDER_BODY,
    POLICY_RENEWAL_REMINDER_PREVIEW_BODY,
    POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
)
from app.services.reminder_resolvers.base import GENERIC_REMINDER_TEMPLATE
from app.services.reminder_resolvers.factory import ReminderResolverFactory


@dataclass(frozen=True)
class ReminderTemplateCatalogEntry:
    id: str
    name: str
    channel: str
    subject: str
    body: str
    module: str | None = None


class ReminderTemplateCatalogService:
    """Assemble a read-only catalog of known reminder templates."""

    def list_templates(self) -> list[ReminderTemplateCatalogEntry]:
        entries: list[ReminderTemplateCatalogEntry] = [
            ReminderTemplateCatalogEntry(
                id="generic_due_notice",
                name="Generic Due Notice",
                channel="email",
                subject="Action required: {{entity_label}}",
                body=GENERIC_REMINDER_TEMPLATE,
                module=None,
            ),
            ReminderTemplateCatalogEntry(
                id="generic_in_app_alert",
                name="In-App Alert",
                channel="in_app",
                subject="Reminder",
                body="{{entity_label}} ({{reference_id}}) needs your attention.",
                module=None,
            ),
            ReminderTemplateCatalogEntry(
                id=POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
                name="Policy Renewal Reminder",
                channel="whatsapp",
                subject="",
                body=POLICY_RENEWAL_REMINDER_PREVIEW_BODY or POLICY_RENEWAL_REMINDER_BODY,
                module="policy",
            ),
        ]

        seen = {entry.id for entry in entries}
        for module in ReminderResolverFactory.list_module_metadata():
            template_id = (module.default_template or "").strip()
            if not template_id or template_id in seen:
                continue
            entries.append(
                ReminderTemplateCatalogEntry(
                    id=template_id,
                    name=template_id.replace("_", " ").title(),
                    channel="whatsapp",
                    subject="",
                    body=GENERIC_REMINDER_TEMPLATE,
                    module=module.id,
                )
            )
            seen.add(template_id)

        return entries
