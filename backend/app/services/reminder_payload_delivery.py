"""Template loading and rendering for payload-mode reminder delivery."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_template import ReminderTemplate
from app.services.reminder_template_service import ReminderTemplateService

WHATSAPP_APPROVAL_APPROVED = "approved"

# Meta-style numbered placeholders → named runtime keys (email/SMS/text channels).
# WhatsApp Meta templates skip this renderer and keep {{1}}..{{4}} for Meta.
_NUMBERED_PLACEHOLDER_KEYS = (
    "customer_name",
    "policy_name",
    "reminder_date",
    "company_name",
)


def render_template_body(body: str, variables: dict[str, Any]) -> str:
    """Replace named and numbered placeholders in template body/subject text.

    Supports:
    - ``{{customer_name}}`` / ``{customer_name}`` (named)
    - ``{{1}}``..``{{4}}`` mapped to customer_name, policy_name, reminder_date,
      company_name (legacy Meta-style bodies copied into email templates)
    """
    rendered = body or ""
    context = {
        key: "" if value is None else str(value) for key, value in (variables or {}).items()
    }
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", value)
        rendered = rendered.replace("{" + key + "}", value)
    for index, key in enumerate(_NUMBERED_PLACEHOLDER_KEYS, start=1):
        rendered = rendered.replace("{{" + str(index) + "}}", context.get(key, ""))
    return rendered


def uses_meta_whatsapp_template(template: ReminderTemplate) -> bool:
    if (template.channel or "").strip().lower() != "whatsapp":
        return False
    approval = (template.approval_status or "").strip().lower()
    template_name = (template.whatsapp_template_name or "").strip()
    return approval == WHATSAPP_APPROVAL_APPROVED and bool(template_name)


async def load_channel_template(
    session: AsyncSession,
    *,
    organization_id: int,
    template_key: str,
    channel: str,
) -> ReminderTemplate:
    definition_name = (template_key or "").strip()
    if not definition_name:
        raise ValueError("template_key is required for payload-mode delivery")

    template = await ReminderTemplateService(session).find_channel_variant(
        organization_id=organization_id,
        definition_name=definition_name,
        channel=channel,
        require_active=True,
    )
    if template is None:
        raise ValueError(
            f"no active template found for template_key={definition_name!r} "
            f"channel={channel!r}"
        )
    body = (template.body or "").strip()
    if not body:
        raise ValueError(
            f"template body is empty for template_key={definition_name!r} "
            f"channel={channel!r}"
        )
    return template


async def validate_template_key_for_channels(
    session: AsyncSession,
    *,
    organization_id: int,
    template_key: str,
    channels: list[str],
) -> None:
    for channel in channels:
        await load_channel_template(
            session,
            organization_id=organization_id,
            template_key=template_key,
            channel=channel,
        )
