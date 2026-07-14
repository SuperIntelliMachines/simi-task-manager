from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.telegram_settings import normalize_telegram_connection_settings, resolve_telegram_bot_token
from app.core.config import get_settings
from app.models.atm005 import ChannelConnection, ContactChannelIdentity
from app.models.atm017 import NotificationPreference
from app.models.core import Contact, Organization, TaskAssignment, User
from app.models.verticals import InsuranceLead, InsurancePolicy
from app.services.channel_service import ChannelService
from app.utils.user_display import format_user_display_name

LEAD_FOLLOWUP_DEDUPE_PREFIX = "lead-followup:"
POLICY_RENEWAL_ENTITY_LABEL = "Policy Renewal"
REMINDER_DATETIME_FORMAT = "%d-%m-%Y %I:%M %p"
logger = logging.getLogger(__name__)


def _outbound_failure_reason(outbound) -> str:
    reason = getattr(outbound, "provider_error", None)
    if reason:
        return str(reason)
    return "outbound message failed"


from app.utils.policy_mobile import normalize_whatsapp_recipient


def _format_policy_reminder_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime(REMINDER_DATETIME_FORMAT)


async def _resolve_policy_whatsapp_sender_name(
    session: AsyncSession,
    *,
    organization_id: int,
    policy: InsurancePolicy,
    explicit_sender_name: str | None = None,
) -> str:
    if explicit_sender_name and explicit_sender_name.strip():
        return explicit_sender_name.strip()
    if policy.assigned_agent_user_id is not None:
        agent = await session.get(User, policy.assigned_agent_user_id)
        if agent is not None and (agent.email or "").strip():
            return format_user_display_name(agent.email)
    org = await session.get(Organization, organization_id)
    if org is not None and (org.name or "").strip():
        return org.name.strip()
    return "SIMI Insurance"


def parse_lead_id_from_dedupe_key(dedupe_key: str) -> int | None:
    if not dedupe_key.startswith(LEAD_FOLLOWUP_DEDUPE_PREFIX):
        return None
    try:
        return int(dedupe_key[len(LEAD_FOLLOWUP_DEDUPE_PREFIX) :])
    except ValueError:
        return None


def policy_type_from_lead_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    for line in notes.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("policy type:"):
            return stripped.split(":", 1)[1].strip() or None
    return None


def policy_email_subject(policy: InsurancePolicy) -> str:
    policy_number = policy.policy_number or f"policy #{policy.id}"
    return f"Premium payment reminder – {policy_number}"


async def resolve_lead_policy_type(session: AsyncSession, lead: InsuranceLead) -> str:
    if lead.related_policy_id is not None:
        policy = await session.get(InsurancePolicy, lead.related_policy_id)
        if policy is not None and policy.policy_type:
            return policy.policy_type
    from_notes = policy_type_from_lead_notes(lead.notes)
    if from_notes:
        return from_notes
    return "insurance"


async def resolve_agent_notification_target(
    session: AsyncSession,
    *,
    organization_id: int,
    user_id: int,
) -> tuple[str, str | None]:
    user = await session.get(User, user_id)
    if user is None:
        return "email", None

    pref_result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == organization_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.contact_id.is_(None),
            NotificationPreference.purpose == "reminder",
        )
    )
    pref = pref_result.scalar_one_or_none()
    if pref is not None and pref.opt_out:
        return pref.preferred_channel, None

    channel = (pref.preferred_channel if pref is not None else "email").strip().lower()
    if channel == "email":
        recipient = (user.email or "").strip() or None
        return channel, recipient

    return channel, (user.email or "").strip() or None


async def resolve_lead_followup_agent_user_id(
    session: AsyncSession,
    *,
    lead: InsuranceLead,
    task_id: int | None,
) -> int | None:
    if lead.assigned_agent_user_id is not None:
        return lead.assigned_agent_user_id
    if task_id is None:
        return None
    assignment_result = await session.execute(
        select(TaskAssignment).where(TaskAssignment.task_id == task_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if assignment is not None and assignment.user_id is not None:
        return assignment.user_id
    return None


async def send_lead_followup_agent_reminder(
    session: AsyncSession,
    *,
    organization_id: int,
    lead_id: int,
    task_id: int,
    message: str,
) -> tuple[bool, str | None, str, str | None]:
    lead = await session.get(InsuranceLead, lead_id)
    if lead is None:
        return False, "lead not found", "", None

    agent_user_id = await resolve_lead_followup_agent_user_id(
        session,
        lead=lead,
        task_id=task_id,
    )
    if agent_user_id is None:
        return False, "no assigned agent", "", None

    channel, recipient = await resolve_agent_notification_target(
        session,
        organization_id=organization_id,
        user_id=agent_user_id,
    )
    if not recipient:
        return False, f"no agent recipient on file for channel {channel}", channel, None

    channel_service = ChannelService(session)
    if channel in {"whatsapp", "telegram"}:
        connections = await channel_service.list_connections(organization_id)
        connection = next(
            (row for row in connections if row.channel == channel and row.status == "active"),
            None,
        )
        if connection is None:
            channel = "email"
            user = await session.get(User, agent_user_id)
            recipient = (user.email or "").strip() if user is not None else None
            if not recipient:
                return False, "no active messaging connection and no agent email", channel, None

    outbound = await channel_service.send_outbound_message(
        organization_id=organization_id,
        channel=channel,
        recipient=recipient,
        text=message,
        task_id=task_id,
        connection_settings={"subject": "Lead follow-up reminder"} if channel == "email" else {},
    )
    if outbound.status == "sent":
        return True, None, channel, recipient
    return False, _outbound_failure_reason(outbound), channel, recipient


async def send_renewal_escalation_agent_notification(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_user_id: int,
    policy_number: str,
    task_id: int,
    message: str,
) -> tuple[bool, str | None]:
    """Email the assigned agent when a policy renewal is escalated."""
    channel, recipient = await resolve_agent_notification_target(
        session,
        organization_id=organization_id,
        user_id=agent_user_id,
    )
    if not recipient:
        return False, f"no agent recipient on file for channel {channel}"

    channel_service = ChannelService(session)
    subject = f"Renewal escalation required – {policy_number}"
    outbound = await channel_service.send_outbound_message(
        organization_id=organization_id,
        channel="email",
        recipient=recipient,
        text=message,
        task_id=task_id,
        connection_settings={"subject": subject},
    )
    if outbound.status == "sent":
        return True, None
    return False, _outbound_failure_reason(outbound)


def _looks_like_telegram_chat_id(value: str) -> bool:
    stripped = value.strip()
    return stripped.isdigit() and len(stripped) >= 5


def _telegram_chat_id_from_policy(policy: InsurancePolicy | None) -> str | None:
    if policy is None:
        return None
    policy_chat_id = getattr(policy, "telegram_chat_id", None)
    if policy_chat_id is not None:
        chat = str(policy_chat_id).strip()
        if _looks_like_telegram_chat_id(chat):
            return chat
    return None


async def _resolve_telegram_chat_recipient(
    session: AsyncSession,
    *,
    organization_id: int,
    contact: Contact,
    policy: InsurancePolicy | None = None,
) -> str | None:
    result = await session.execute(
        select(ContactChannelIdentity).where(
            ContactChannelIdentity.organization_id == organization_id,
            ContactChannelIdentity.contact_id == contact.id,
            ContactChannelIdentity.channel == "telegram",
        )
    )
    identity = result.scalar_one_or_none()
    if identity is not None:
        if identity.external_chat_id:
            return identity.external_chat_id
        if identity.external_user_id:
            return identity.external_user_id

    return _telegram_chat_id_from_policy(policy)


async def _resolve_active_telegram_connection(
    session: AsyncSession,
    organization_id: int,
) -> ChannelConnection | None:
    channel_service = ChannelService(session)
    connections = await channel_service.list_connections(organization_id)
    return next(
        (row for row in connections if row.channel == "telegram" and row.status == "active"),
        None,
    )


def _telegram_delivery_available(connection: ChannelConnection | None) -> bool:
    settings = get_settings()
    customer_token = settings.telegram_customer_bot_token.strip()
    if customer_token:
        return True
    if connection is not None and resolve_telegram_bot_token(connection.settings or {}):
        return True
    return bool(resolve_telegram_bot_token())


def _whatsapp_delivery_available(connection: ChannelConnection | None) -> bool:
    settings = get_settings()
    if connection is not None and (connection.status or "").strip().lower() == "active":
        return True
    return bool(
        settings.whatsapp_access_token.strip()
        and settings.whatsapp_phone_number_id.strip()
    )


async def resolve_policy_message_recipient(
    session: AsyncSession,
    *,
    organization_id: int,
    contact: Contact,
    channel: str,
    policy: InsurancePolicy | None = None,
) -> str | None:
    channel = channel.strip().lower()
    if channel == "email":
        email = (contact.email or "").strip()
        return email or None

    if channel == "telegram":
        recipient = await _resolve_telegram_chat_recipient(
            session,
            organization_id=organization_id,
            contact=contact,
            policy=policy,
        )
        if recipient:
            return recipient
        logger.warning(
            "[InsuranceMessaging] missing telegram_chat_id policy_id=%s contact_id=%s",
            getattr(policy, "id", None),
            contact.id,
        )
        return None

    mobile = (contact.phone or "").strip()
    if not mobile:
        return None
    if channel in {"whatsapp", "sms"}:
        if channel == "whatsapp":
            normalized = normalize_whatsapp_recipient(mobile)
        else:
            normalized = "".join(char for char in mobile if char.isdigit() or char == "+")
        return normalized or None
    return mobile


async def _send_policy_email_message(
    session: AsyncSession,
    *,
    organization_id: int,
    policy: InsurancePolicy,
    contact: Contact,
    message: str,
) -> tuple[bool, str | None]:
    email = (contact.email or "").strip()
    if not email:
        return False, "no recipient on file for channel email"

    channel_service = ChannelService(session)
    outbound = await channel_service.send_outbound_message(
        organization_id=organization_id,
        channel="email",
        recipient=email,
        text=message,
        connection_settings={"subject": policy_email_subject(policy)},
        contact_id=policy.policyholder_id,
    )
    if outbound.status == "sent":
        return True, None
    return False, _outbound_failure_reason(outbound)


async def send_policy_channel_message(
    session: AsyncSession,
    *,
    organization_id: int,
    policy: InsurancePolicy,
    contact: Contact,
    channel: str,
    message: str,
    sender_name: str | None = None,
    reminder_date: datetime | None = None,
) -> tuple[bool, str | None]:
    channel = channel.strip().lower()
    logger.info(
        "[InsuranceMessaging] send_policy_channel_message ENTER policy_id=%s org_id=%s channel=%s "
        "contact_id=%s telegram_chat_id=%s contact_phone=%r contact_email=%r",
        getattr(policy, "id", None),
        organization_id,
        channel,
        contact.id,
        getattr(policy, "telegram_chat_id", None),
        contact.phone,
        contact.email,
    )
    if channel == "email":
        return await _send_policy_email_message(
            session,
            organization_id=organization_id,
            policy=policy,
            contact=contact,
            message=message,
        )

    recipient = await resolve_policy_message_recipient(
        session,
        organization_id=organization_id,
        contact=contact,
        channel=channel,
        policy=policy,
    )
    if not recipient:
        error = f"no recipient on file for channel {channel}"
        logger.warning(
            "[InsuranceMessaging] send_policy_channel_message EXIT policy_id=%s channel=%s success=False error=%s",
            getattr(policy, "id", None),
            channel,
            error,
        )
        return False, error

    channel_service = ChannelService(session)
    if channel == "telegram":
        connection = await _resolve_active_telegram_connection(session, organization_id)
        if not _telegram_delivery_available(connection):
            if (contact.email or "").strip():
                return await _send_policy_email_message(
                    session,
                    organization_id=organization_id,
                    policy=policy,
                    contact=contact,
                    message=message,
                )
            error = "no active telegram connection or bot token"
            logger.warning(
                "[InsuranceMessaging] send_policy_channel_message EXIT policy_id=%s channel=%s success=False error=%s",
                getattr(policy, "id", None),
                channel,
                error,
            )
            return False, error
        settings = get_settings()
        if settings.telegram_customer_bot_token.strip():
            connection_settings = {"bot_token": settings.telegram_customer_bot_token.strip()}
        else:
            connection_settings = normalize_telegram_connection_settings(
                connection.settings if connection is not None else {}
            )
        outbound = await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=channel,
            recipient=recipient.replace(" ", ""),
            text=message,
            connection_settings=connection_settings,
            contact_id=policy.policyholder_id,
        )
    elif channel == "whatsapp":
        logger.info(
            "[InsuranceMessaging] whatsapp lookup start organization_id=%s requested_channel=%s",
            organization_id,
            channel,
        )
        connections = await channel_service.list_connections(organization_id)
        logger.info(
            "[InsuranceMessaging] whatsapp lookup rows_returned=%s organization_id=%s",
            len(connections),
            organization_id,
        )
        for row in connections:
            logger.info(
                "[InsuranceMessaging] channel_connection row organization_id=%s id=%s channel=%s status=%s",
                organization_id,
                getattr(row, "id", None),
                row.channel,
                row.status,
            )
        connection = next(
            (row for row in connections if row.channel == channel and row.status == "active"),
            None,
        )
        if connection is not None:
            logger.info(
                "[InsuranceMessaging] whatsapp lookup matched id=%s channel=%s status=%s",
                getattr(connection, "id", None),
                connection.channel,
                connection.status,
            )
        if not _whatsapp_delivery_available(connection):
            logger.warning(
                "[InsuranceMessaging] whatsapp lookup no-match organization_id=%s requested_channel=%s required_status=active",
                organization_id,
                channel,
            )
            return False, f"no active {channel} connection"
        outbound_connection_settings = dict(connection.settings if connection is not None else {})
        # Policy reminders must always use approved template sends (not 24h session text).
        outbound_connection_settings["use_whatsapp_session_text"] = False
        resolved_sender_name = await _resolve_policy_whatsapp_sender_name(
            session,
            organization_id=organization_id,
            policy=policy,
            explicit_sender_name=sender_name,
        )
        reminder_date_value = reminder_date or policy.expiry_date
        outbound = await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=channel,
            recipient=recipient.replace(" ", ""),
            text=message,
            connection_settings=outbound_connection_settings,
            template_name="policy_renewal_reminder",
            template_language="en_US",
            template_variables={
                "customer_name": (contact.name or "Customer").strip() or "Customer",
                "entity_label": POLICY_RENEWAL_ENTITY_LABEL,
                "reminder_date": _format_policy_reminder_datetime(reminder_date_value),
                "sender_name": resolved_sender_name,
            },
            contact_id=policy.policyholder_id,
        )
        logger.info(
            "[InsuranceMessaging] whatsapp outbound policy_id=%s recipient=%s status=%s provider_id=%s",
            getattr(policy, "id", None),
            recipient,
            outbound.status,
            getattr(outbound, "external_provider_message_id", None),
        )
    else:
        outbound = await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=channel,
            recipient=recipient,
            text=message,
            contact_id=policy.policyholder_id,
        )

    if outbound.status == "sent":
        logger.info(
            "[InsuranceMessaging] send_policy_channel_message EXIT policy_id=%s channel=%s success=True",
            getattr(policy, "id", None),
            channel,
        )
        return True, None
    failure = _outbound_failure_reason(outbound)
    logger.warning(
        "[InsuranceMessaging] send_policy_channel_message EXIT policy_id=%s channel=%s success=False error=%s",
        getattr(policy, "id", None),
        channel,
        failure,
    )
    return False, failure
