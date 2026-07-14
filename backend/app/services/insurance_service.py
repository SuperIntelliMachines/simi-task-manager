from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, time
from urllib.parse import quote

from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.policy_classifier import (
    is_grace_period,
    is_lapsed,
    sort_policies_default_order,
)
from app.utils.policy_email import validate_policy_email
from app.utils.policy_queries import select_insurance_policies
from app.utils.policy_reminder_settings import (
    REMINDER_TYPE_DEFAULT,
    REMINDER_TYPE_PERSONALIZED,
    parse_time_hhmm,
    validate_policy_reminder_settings,
)
from app.utils.preferred_channels import normalize_preferred_channel, resolve_policy_reminder_channels
from app.utils.policy_mobile import mobile_policy_lookup_values
from app.utils.renewal_frequency import RENEWAL_FREQUENCY_DEFAULT, validate_renewal_frequency
from app.utils.policy_status import (
    POLICY_STATUS_ACTIVE,
    evaluate_policy_status,
    normalize_grace_period_days,
)

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import attributes as orm_attributes
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.atm017 import MessageTemplate, NotificationPreference
from app.models.core import Contact, Reminder, Task, WorkflowRun, WorkflowTemplate
from app.models.insurance import PolicyCustomReminder, PolicyReminder
from app.models.verticals import InsuranceLead, InsurancePolicy
from app.core.config import get_settings
from app.schemas.custom_reminder_fields import CustomReminderSchema
from app.utils.user_display import format_user_display_name
from app.services.audit_service import write_audit_event
from app.services.insurance_messaging import send_policy_channel_message
from app.services.policy_reminder_messages import build_policy_reminder_message
from app.services.message_template_service import extract_template_variables
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

RENEWAL_REMINDER_STAGE_DEFINITION = "30,15,10,5,2,1,0"
DEFAULT_RENEWAL_REMINDER_CHANNEL = "whatsapp"
LIC_PREMIUM_PAYMENT_URL = "https://ebiz.licindia.in/spy-LIC"
PREMIUM_PAYMENT_DUE_TEMPLATE = (
    "Dear {customer_name},\n\n"
    "Premium due for Policy No. {policy_number} has not yet been received.\n\n"
    "Please pay your premium online:\n"
    f"{LIC_PREMIUM_PAYMENT_URL}\n\n"
    "Kindly ignore this message if payment has already been made.\n\n"
    "Thank you,\n"
    "{logged_in_user_name}"
)
RENEWAL_CONFIRMATION_TEMPLATE = (
    "Dear {customer_name},\n\n"
    "Your policy {policy_number} has been renewed successfully.\n\n"
    "Thank you for choosing our services."
)
AGENT_FOLLOW_UP_TEMPLATE = (
    "Follow up with {customer_name}\n"
    "regarding the {policy_type} policy decision."
)


def build_premium_payment_due_message(
    *,
    customer_name: str,
    policy_number: str,
    logged_in_user_name: str,
) -> str:
    return PREMIUM_PAYMENT_DUE_TEMPLATE.format(
        customer_name=customer_name or "Customer",
        policy_number=policy_number or "-",
        logged_in_user_name=logged_in_user_name or "SIMI Insurance",
    )


def build_renewal_confirmation_message(
    *,
    customer_name: str,
    policy_number: str,
) -> str:
    return RENEWAL_CONFIRMATION_TEMPLATE.format(
        customer_name=customer_name or "Customer",
        policy_number=policy_number or "-",
    )


def build_agent_follow_up_message(
    *,
    customer_name: str,
    policy_type: str | None = None,
) -> str:
    return AGENT_FOLLOW_UP_TEMPLATE.format(
        customer_name=customer_name or "the customer",
        policy_type=((policy_type or "insurance").strip().lower() or "insurance"),
    )


INSURANCE_TEMPLATE_DEFINITIONS = [
    {
        "name": "insurance_premium_due_soon",
        "purpose": "premium_due_soon",
        "body": "Hi {policyholder_name}, your premium for policy {policy_number} is due soon.",
    },
    {
        "name": "insurance_policy_expires_today",
        "purpose": "policy_expires_today",
        "body": "Hi {policyholder_name}, policy {policy_number} expires today.",
    },
    {
        "name": "insurance_policy_expired",
        "purpose": "policy_expired",
        "body": "Hi {policyholder_name}, policy {policy_number} has expired. Please renew as soon as possible.",
    },
    {
        "name": "insurance_agent_follow_up",
        "purpose": "agent_follow_up",
        "body": AGENT_FOLLOW_UP_TEMPLATE,
    },
    {
        "name": "insurance_renewal_confirmation",
        "purpose": "renewal_confirmation",
        "body": RENEWAL_CONFIRMATION_TEMPLATE,
    },
    {
        "name": "insurance_renewal_reminder_sms",
        "purpose": "renewal_reminder_sms",
        "body": PREMIUM_PAYMENT_DUE_TEMPLATE,
    },
    {
        "name": "insurance_premium_payment_due",
        "purpose": "premium_payment_due",
        "body": PREMIUM_PAYMENT_DUE_TEMPLATE,
    },
]


OPEN_LEAD_STATUSES = {"open", "follow_up_pending", "follow_up_later", "interested"}
LEAD_FOLLOWUP_ACTION_STATUSES = {"interested", "not_interested", "follow_up_later"}
CLOSED_LEAD_STATUSES = {"not_interested", "renewed"}


# utcnow_naive imported from utils


class InsuranceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_service = TaskService(session)
        self.reminder_service = ReminderService(session)
        self.workflow_service = WorkflowService(session)

    async def _inherit_telegram_linkage(
        self, mobile_number: str | None
    ) -> tuple[int | None, str | None]:
        """Copy Telegram linkage from the latest policy with the same mobile number."""
        lookup_values = mobile_policy_lookup_values(mobile_number)
        if not lookup_values:
            return None, None
        result = await self.session.execute(
            select(InsurancePolicy)
            .where(
                InsurancePolicy.telegram_chat_id.isnot(None),
                InsurancePolicy.mobile_number.in_(lookup_values),
            )
            .order_by(InsurancePolicy.id.desc())
            .limit(1)
        )
        source = result.scalar_one_or_none()
        if source is None:
            return None, None
        logger.info(
            "[create_policy] inherited telegram_chat_id=%s from policy_id=%s mobile=%s",
            source.telegram_chat_id,
            source.id,
            mobile_number,
        )
        return source.telegram_chat_id, source.telegram_username

    async def create_policy(
        self,
        *,
        organization_id: int,
        policyholder_name: str,
        expiry_date: datetime,
        actor_user_id: int | None,
        policy_number: str | None = None,
        premium: int = 0,
        policy_type: str | None = None,
        carrier: str | None = None,
        renewal_frequency: str | None = None,
        grace_period_days: int | None = None,
        assigned_agent_user_id: int | None = None,
        preferred_channel: list[str] | str | None = None,
        reminder_type: str | None = "default",
        reminder_unit: str | None = None,
        reminder_value: int | None = None,
        dnd_start_time: time | str | None = None,
        dnd_end_time: time | str | None = None,
        custom_reminders: list | None = None,
        contact_phone: str | None = None,
        contact_email: str | None = None,
    ) -> InsurancePolicy:
        contact, _ = await self._resolve_contact(
            organization_id=organization_id,
            name=policyholder_name,
            allow_create=True,
            phone=contact_phone,
            email=contact_email,
        )
        policy_number = policy_number or self._generate_policy_number(organization_id, contact.id)
        if policy_number:
            existing = await self.session.execute(
                select(InsurancePolicy).where(InsurancePolicy.policy_number == policy_number)
            )
            if existing.scalar_one_or_none() is not None:
                raise ValueError("Policy number already exists.")
        now = utcnow_naive()
        expiry_date = normalize_to_utc_naive(expiry_date)
        policy_email = validate_policy_email(contact_email)
        normalized_frequency = validate_renewal_frequency(renewal_frequency or RENEWAL_FREQUENCY_DEFAULT)
        normalized_custom = self._normalize_custom_reminders_payload(custom_reminders)
        reminder_settings = validate_policy_reminder_settings(
            reminder_type=reminder_type,
            reminder_unit=reminder_unit,
            reminder_value=reminder_value,
            dnd_start_time=dnd_start_time,
            dnd_end_time=dnd_end_time,
            has_custom_reminders=bool(normalized_custom),
        )
        logger.info(
            "[create_policy] dnd_start_time=%s dnd_end_time=%s custom_reminders=%s",
            reminder_settings["dnd_start_time"],
            reminder_settings["dnd_end_time"],
            normalized_custom,
        )
        from app.utils.preferred_channels import coerce_preferred_channel_input

        normalized_channels = normalize_preferred_channel(
            coerce_preferred_channel_input(preferred_channel)
        )
        mobile_number = contact_phone.strip() if contact_phone else None
        telegram_chat_id, telegram_username = await self._inherit_telegram_linkage(mobile_number)
        policy = InsurancePolicy(
            organization_id=organization_id,
            policyholder_id=contact.id,
            policy_number=policy_number,
            premium=premium,
            policy_type=policy_type,
            carrier=carrier,
            renewal_frequency=normalized_frequency,
            grace_period_days=normalize_grace_period_days(grace_period_days),
            assigned_agent_user_id=assigned_agent_user_id,
            preferred_channel=normalized_channels,
            reminder_type=reminder_settings["reminder_type"],
            reminder_unit=reminder_settings["reminder_unit"],
            reminder_value=reminder_settings["reminder_value"],
            dnd_start_time=reminder_settings["dnd_start_time"],
            dnd_end_time=reminder_settings["dnd_end_time"],
            mobile_number=mobile_number,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
            email=policy_email,
            expiry_date=expiry_date,
            status=POLICY_STATUS_ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self.session.add(policy)
        await self.session.flush()
        logger.info(
            "[create_policy] flushed policy id=%s reminder_type=%s custom_reminders=%s",
            policy.id,
            reminder_settings["reminder_type"],
            normalized_custom,
        )
        if (
            normalized_custom
            and reminder_settings["reminder_type"] == REMINDER_TYPE_PERSONALIZED
        ):
            # Legacy policy_custom_reminders table is deprecated for new schedules.
            pass
        await self.session.commit()
        if normalized_channels:
            await self._ensure_notification_preference(
                organization_id=organization_id,
                contact_id=contact.id,
                preferred_channel=normalized_channels[0],
            )
        await self.ensure_default_templates(organization_id)
        return policy

    async def list_policies(self, organization_id: int, status: str | None = None) -> list[InsurancePolicy]:
        logger = logging.getLogger(__name__)
        # Active policies are strictly those still within renewal date.
        if status == "active":
            from app.utils.policy_classifier import is_active_policy, is_critical_renewal, is_due_renewal

            result = await self.session.execute(
                select_insurance_policies()
                .where(InsurancePolicy.organization_id == organization_id)
                .order_by(InsurancePolicy.expiry_date.asc())
            )
            rows = list(result.scalars().unique().all())
            for policy in rows:
                policy.status = evaluate_policy_status(policy)
            active = [p for p in rows if is_active_policy(p)]
            grace_period = [p for p in rows if is_grace_period(p)]
            lapsed = [p for p in rows if is_lapsed(p)]
            logger.info(
                "[list_policies.active] org=%s total=%d active=%d due=%d critical=%d grace=%d lapsed=%d",
                organization_id,
                len(rows),
                len(active),
                sum(1 for p in active if is_due_renewal(p)),
                sum(1 for p in active if is_critical_renewal(p)),
                len(grace_period),
                len(lapsed),
            )
            return sort_policies_default_order(active)

        if status in {"grace_period", "lapsed"}:
            result = await self.session.execute(
                select_insurance_policies()
                .where(InsurancePolicy.organization_id == organization_id)
                .order_by(InsurancePolicy.expiry_date.asc())
            )
            rows = list(result.scalars().unique().all())
            for policy in rows:
                policy.status = evaluate_policy_status(policy)
            bucket = [p for p in rows if evaluate_policy_status(p) == status]
            logger.info("[list_policies.%s] org=%s total=%d bucket=%d", status, organization_id, len(rows), len(bucket))
            return sort_policies_default_order(bucket)

        query = select_insurance_policies().where(InsurancePolicy.organization_id == organization_id)
        if status is not None:
            query = query.where(InsurancePolicy.status == status)
        result = await self.session.execute(query.order_by(InsurancePolicy.expiry_date.asc()))
        rows = list(result.scalars().unique().all())
        for policy in rows:
            policy.status = evaluate_policy_status(policy)
        return sort_policies_default_order(rows)

    async def update_policy(self, policy_id: int, updates: dict) -> InsurancePolicy:
        policy = await self.session.get(InsurancePolicy, policy_id)
        if policy is None:
            raise ValueError("policy not found")
        policyholder_name = updates.pop("policyholder_name", None)
        email_present = "email" in updates
        email_update = updates.pop("email", None) if email_present else None
        contact = None
        if policyholder_name is not None or email_present:
            contact = await self.session.get(Contact, policy.policyholder_id)
        if policyholder_name is not None and contact is not None:
            contact.name = policyholder_name.strip()
            contact.updated_at = utcnow_naive()
        if email_present:
            normalized_email = validate_policy_email(email_update)
            policy.email = normalized_email
            if contact is None:
                contact = await self.session.get(Contact, policy.policyholder_id)
            if contact is not None:
                contact.email = normalized_email
                contact.updated_at = utcnow_naive()
        custom_reminders = updates.pop("custom_reminders", None)
        normalized_custom = self._normalize_custom_reminders_payload(custom_reminders)
        reminder_keys = ("reminder_type", "reminder_unit", "reminder_value", "dnd_start_time", "dnd_end_time")
        if normalized_custom is not None or any(key in updates for key in reminder_keys):
            validated = validate_policy_reminder_settings(
                reminder_type=updates.get("reminder_type", getattr(policy, "reminder_type", None)),
                reminder_unit=updates.get("reminder_unit", getattr(policy, "reminder_unit", None)),
                reminder_value=updates.get("reminder_value", getattr(policy, "reminder_value", None)),
                dnd_start_time=updates.get("dnd_start_time", getattr(policy, "dnd_start_time", None)),
                dnd_end_time=updates.get("dnd_end_time", getattr(policy, "dnd_end_time", None)),
                has_custom_reminders=normalized_custom is not None,
            )
            updates.update(validated)
        parent_dnd_start, parent_dnd_end = self._parse_policy_dnd_pair(
            updates.get("dnd_start_time", getattr(policy, "dnd_start_time", None)),
            updates.get("dnd_end_time", getattr(policy, "dnd_end_time", None)),
        )
        logger.info(
            "[update_policy] policy_id=%s dnd_start_time=%s dnd_end_time=%s custom_reminders=%s",
            policy_id,
            parent_dnd_start,
            parent_dnd_end,
            normalized_custom,
        )
        if "preferred_channel" in updates:
            from app.utils.preferred_channels import coerce_preferred_channel_input

            updates["preferred_channel"] = normalize_preferred_channel(
                coerce_preferred_channel_input(updates.get("preferred_channel"))
            )
        for key, value in updates.items():
            setattr(policy, key, value)
        policy.status = evaluate_policy_status(policy)
        policy.updated_at = utcnow_naive()

        if normalized_custom is not None:
            # Legacy policy_custom_reminders table is deprecated for new schedules.
            pass
        elif updates.get("reminder_type") == REMINDER_TYPE_DEFAULT:
            pass

        await self.session.commit()

        if policy.preferred_channel:
            await self._ensure_notification_preference(
                organization_id=policy.organization_id,
                contact_id=policy.policyholder_id,
                preferred_channel=policy.preferred_channel[0],
            )
        return policy

    async def start_policy_renewal_workflow(
        self,
        *,
        policy_id: int,
        actor_user_id: int | None,
    ) -> dict[str, object]:
        policy = await self._get_policy(policy_id)
        await self.ensure_default_templates(policy.organization_id)
        template = await self._ensure_workflow_template(
            organization_id=policy.organization_id,
            name="policy_renewal_workflow",
            definition=f"expiry {RENEWAL_REMINDER_STAGE_DEFINITION}",
        )
        root_task = await self.task_service.create_task(
            organization_id=policy.organization_id,
            title=f"Policy renewal for {policy.policy_number}",
            description=f"Renewal reminders for policy {policy.policy_number}",
            due_at=policy.expiry_date + timedelta(days=1),
            domain="insurance",
            actor_user_id=actor_user_id,
        )
        escalation_task = await self.task_service.create_task(
            organization_id=policy.organization_id,
            title=f"Escalate renewal for {policy.policy_number}",
            description="Escalate to assigned agent if the policy is still not renewed.",
            due_at=policy.expiry_date + timedelta(days=1),
            domain="insurance",
            actor_user_id=actor_user_id,
        )
        if policy.assigned_agent_user_id is not None:
            await self.task_service.assign_task(
                task_id=root_task.id,
                organization_id=policy.organization_id,
                user_id=policy.assigned_agent_user_id,
                contact_id=None,
                actor_user_id=actor_user_id,
            )
            await self.task_service.assign_task(
                task_id=escalation_task.id,
                organization_id=policy.organization_id,
                user_id=policy.assigned_agent_user_id,
                contact_id=None,
                actor_user_id=actor_user_id,
            )
        run = await self.workflow_service.start_workflow_run(
            organization_id=policy.organization_id,
            workflow_template_id=template.id,
            task_id=root_task.id,
            current_step="scheduled",
            actor_user_id=actor_user_id,
        )
        payload = {
            "policy_id": policy.id,
            "task_id": root_task.id,
            "escalation_task_id": escalation_task.id,
            "preferred_channel": policy.preferred_channel,
            "reminder_stages": RENEWAL_REMINDER_STAGE_DEFINITION,
        }
        await self.workflow_service.advance_workflow_state(
            run.id,
            current_step="scheduled",
            state_payload=json.dumps(payload),
            actor_user_id=actor_user_id,
        )
        return {
            "policy": policy,
            "workflow_template": template,
            "workflow_run": run,
            "root_task": root_task,
            "escalation_task": escalation_task,
            "reminders": [],
        }

    async def send_policy_renewal_sms(
        self,
        *,
        policy_id: int,
        actor_user_id: int | None = None,
        logged_in_user_name: str | None = None,
    ) -> dict[str, str | None]:
        policy = await self._get_policy(policy_id)
        contact = await self.session.get(Contact, policy.policyholder_id)
        mobile = (contact.phone or "").strip() if contact else ""
        if not mobile:
            raise ValueError("no mobile number on file")

        policyholder_name = (contact.name if contact else None) or "Customer"
        sender_name = await self._resolve_logged_in_user_name(
            actor_user_id=actor_user_id,
            explicit_name=logged_in_user_name,
        )
        message = build_premium_payment_due_message(
            customer_name=policyholder_name,
            policy_number=policy.policy_number,
            logged_in_user_name=sender_name,
        )
        channels = resolve_policy_reminder_channels(getattr(policy, "preferred_channel", None))
        channel = channels[0] if channels else "sms"
        logger.info(
            "Premium payment due reminder policy_id=%s policy_number=%s channel=%s mobile=%s logged_in_user=%s message=%s",
            policy_id,
            policy.policy_number,
            channel or "sms",
            mobile,
            sender_name,
            message,
        )

        if channel in ("whatsapp", "telegram") and contact is not None:
            if channel == "whatsapp":
                logger.info(
                    "[InsuranceService] send_policy_renewal_sms policy_id=%s payload_type=template "
                    "template_name=policy_renewal_reminder template_language=en_US channel=whatsapp",
                    policy_id,
                )
            send_success, send_error = await send_policy_channel_message(
                self.session,
                organization_id=policy.organization_id,
                policy=policy,
                contact=contact,
                channel=channel,
                message="Policy renewal reminder",
                sender_name=sender_name,
                reminder_date=policy.expiry_date,
            )
            if send_success:
                return {
                    "mode": "sent",
                    "mobile": mobile,
                    "policyholder_name": policyholder_name,
                    "policy_number": policy.policy_number,
                    "payment_link": LIC_PREMIUM_PAYMENT_URL,
                    "logged_in_user_name": sender_name,
                    "message": "Policy renewal reminder",
                    "sms_uri": None,
                }
            logger.warning(
                "[InsuranceService] send_policy_renewal_sms policy_id=%s channel=%s send_failed error=%s",
                policy_id,
                channel,
                send_error,
            )

        normalized = "".join(char for char in mobile if char.isdigit() or char == "+")
        if not normalized:
            raise ValueError("no mobile number on file")

        return {
            "mode": "client",
            "mobile": mobile,
            "policyholder_name": policyholder_name,
            "policy_number": policy.policy_number,
            "payment_link": LIC_PREMIUM_PAYMENT_URL,
            "logged_in_user_name": sender_name,
            "message": message,
            "sms_uri": f"sms:{normalized}?body={quote(message)}",
        }

    def _escalation_task_title(self, policy_number: str) -> str:
        return f"Escalate renewal for {policy_number}"

    async def _find_open_escalation_task(self, policy: InsurancePolicy) -> Task | None:
        result = await self.session.execute(
            select(Task).where(
                Task.organization_id == policy.organization_id,
                Task.domain == "insurance",
                Task.title == self._escalation_task_title(policy.policy_number),
                Task.status.in_(["open", "snoozed"]),
            )
        )
        return result.scalars().first()

    async def trigger_renewal_escalation(
        self,
        *,
        policy: InsurancePolicy,
        actor_user_id: int | None = None,
    ) -> dict[str, object]:
        existing = await self._find_open_escalation_task(policy)
        if existing is not None:
            result = {
                "result": "skipped",
                "reason": "open escalation task already exists",
                "task_id": existing.id,
            }
            logger.info(
                "[PolicyRenewalEscalation] policy_id=%s task_id=%s assigned_agent=%s escalation_result=%s",
                policy.id,
                existing.id,
                policy.assigned_agent_user_id,
                result,
            )
            return result

        now = utcnow_naive()
        task = await self.task_service.create_task(
            organization_id=policy.organization_id,
            title=self._escalation_task_title(policy.policy_number),
            description="Policy has not been renewed after expiry. Immediate follow-up required.",
            due_at=now,
            domain="insurance",
            actor_user_id=actor_user_id,
        )
        if policy.assigned_agent_user_id is not None:
            await self.task_service.assign_task(
                task_id=task.id,
                organization_id=policy.organization_id,
                user_id=policy.assigned_agent_user_id,
                contact_id=None,
                actor_user_id=actor_user_id,
            )

        policy.status = evaluate_policy_status(policy)
        policy.updated_at = now

        await write_audit_event(
            session=self.session,
            organization_id=policy.organization_id,
            actor_user_id=actor_user_id,
            event_type="policy.escalated",
            entity_type="policy",
            entity_id=str(policy.id),
            payload={
                "task_id": task.id,
                "assigned_agent_user_id": policy.assigned_agent_user_id,
                "policy_number": policy.policy_number,
            },
        )

        result = {
            "result": "created",
            "task_id": task.id,
            "assigned_agent_user_id": policy.assigned_agent_user_id,
        }
        logger.info(
            "[PolicyRenewalEscalation] policy_id=%s task_id=%s assigned_agent=%s escalation_result=%s",
            policy.id,
            task.id,
            policy.assigned_agent_user_id,
            result,
        )
        return result

    async def mark_policy_renewed(
        self,
        *,
        policy_id: int,
        actor_user_id: int | None,
        new_expiry_date: datetime | None = None,
        send_confirmation: bool = True,
    ) -> InsurancePolicy:
        policy = await self._get_policy(policy_id)
        now = utcnow_naive()

        if new_expiry_date is not None:
            policy.expiry_date = normalize_to_utc_naive(new_expiry_date)

        policy.status = POLICY_STATUS_ACTIVE
        policy.updated_at = now

        cancelled_policy_reminders = await self._cancel_renewal_policy_reminders(policy)
        cancelled_core_reminders = await self._cancel_core_renewal_reminders(policy)
        await self.session.commit()

        workflow_stats = await self._complete_policy_workflow(policy=policy, actor_user_id=actor_user_id)

        confirmation_sent = False
        confirmation_error: str | None = None
        if send_confirmation:
            confirmation_sent, confirmation_error = await self._send_renewal_confirmation(
                policy=policy,
                actor_user_id=actor_user_id,
            )

        await write_audit_event(
            session=self.session,
            organization_id=policy.organization_id,
            actor_user_id=actor_user_id,
            event_type="policy.renewed",
            entity_type="policy",
            entity_id=str(policy.id),
            payload={
                "cancelled_policy_reminders": cancelled_policy_reminders,
                "cancelled_core_reminders": cancelled_core_reminders,
                "cancelled_workflows": workflow_stats["cancelled_workflows"],
                "completed_tasks": workflow_stats["completed_tasks"],
                "cancelled_escalations": workflow_stats["cancelled_escalations"],
                "confirmation_sent": confirmation_sent,
                "confirmation_error": confirmation_error,
                "new_expiry_date": policy.expiry_date.isoformat() if policy.expiry_date else None,
            },
        )
        await self.session.commit()
        await self.session.refresh(policy)

        logger.info(
            "[mark_policy_renewed] policy_id=%s cancelled_policy_reminders=%s cancelled_core_reminders=%s "
            "cancelled_workflows=%s cancelled_escalations=%s confirmation_sent=%s confirmation_error=%s",
            policy.id,
            cancelled_policy_reminders,
            cancelled_core_reminders,
            workflow_stats["cancelled_workflows"],
            workflow_stats["cancelled_escalations"],
            confirmation_sent,
            confirmation_error,
        )
        return policy

    async def list_policy_reminders(self, policy_id: int) -> list[PolicyReminder]:
        await self._get_policy(policy_id)
        result = await self.session.execute(
            select(PolicyReminder)
            .where(PolicyReminder.policy_id == policy_id)
            .order_by(PolicyReminder.reminder_at.asc())
        )
        return list(result.scalars())

    async def renew_policy_with_new_expiry(
        self,
        *,
        policy_id: int,
        new_expiry_date: datetime,
        renewal_notes: str | None = None,
        actor_user_id: int | None = None,
    ) -> tuple[InsurancePolicy, list[PolicyReminder]]:
        from app.jobs.policy_reminder_generator import ensure_policy_reminder_schedule_for_policy
        policy = await self._get_policy(policy_id)
        now = utcnow_naive()

        previous_expiry = normalize_to_utc_naive(policy.expiry_date)
        normalized_new_expiry = normalize_to_utc_naive(new_expiry_date)
        if previous_expiry is None or normalized_new_expiry is None:
            raise ValueError("expiry date is required")
        if normalized_new_expiry.date() <= previous_expiry.date():
            raise ValueError("new expiry date must be after the current expiry date")

        cancelled_policy_reminders = await self._cancel_renewal_policy_reminders(policy)
        cancelled_core_reminders = await self._cancel_core_renewal_reminders(policy)
        workflow_stats = await self._complete_policy_workflow(policy=policy, actor_user_id=actor_user_id)

        policy.expiry_date = normalized_new_expiry
        policy.status = POLICY_STATUS_ACTIVE
        policy.updated_at = now

        reminders_created = await ensure_policy_reminder_schedule_for_policy(self.session, policy)

        await write_audit_event(
            session=self.session,
            organization_id=policy.organization_id,
            actor_user_id=actor_user_id,
            event_type="policy.renewed",
            entity_type="policy",
            entity_id=str(policy.id),
            payload={
                "previous_expiry_date": previous_expiry.isoformat(),
                "new_expiry_date": normalized_new_expiry.isoformat(),
                "renewal_notes": (renewal_notes or "").strip() or None,
                "cancelled_policy_reminders": cancelled_policy_reminders,
                "cancelled_core_reminders": cancelled_core_reminders,
                "cancelled_workflows": workflow_stats["cancelled_workflows"],
                "completed_tasks": workflow_stats["completed_tasks"],
                "cancelled_escalations": workflow_stats["cancelled_escalations"],
                "reminders_created": reminders_created,
            },
        )
        await self.session.commit()
        await self.session.refresh(policy)

        reminders = await self.list_policy_reminders(policy.id)
        logger.info(
            "[renew_policy_with_new_expiry] policy_id=%s previous_expiry=%s new_expiry=%s "
            "cancelled_policy_reminders=%s reminders_created=%s total_reminders=%s",
            policy.id,
            previous_expiry.date().isoformat(),
            normalized_new_expiry.date().isoformat(),
            cancelled_policy_reminders,
            reminders_created,
            len(reminders),
        )
        return policy, reminders

    async def create_lead(
        self,
        *,
        organization_id: int,
        contact_name: str,
        actor_user_id: int | None,
        assigned_agent_user_id: int | None = None,
        source: str | None = None,
        notes: str | None = None,
        demo_logged_at: datetime | None = None,
        followup_due_at: datetime | None = None,
        related_policy_id: int | None = None,
        contact_phone: str | None = None,
        contact_email: str | None = None,
        insurance_type: str | None = None,
        status: str | None = None,
    ) -> InsuranceLead:
        contact, _ = await self._resolve_contact(
            organization_id=organization_id,
            name=contact_name,
            allow_create=True,
            phone=contact_phone,
            email=contact_email,
        )
        now = utcnow_naive()
        # normalize incoming datetimes to timezone-naive UTC before storing
        demo_logged_at = normalize_to_utc_naive(demo_logged_at)
        followup_due_at = normalize_to_utc_naive(followup_due_at)

        lead_notes = notes
        if insurance_type:
            label = insurance_type.strip().capitalize()
            prefix = f"Policy Type: {label}"
            lead_notes = f"{prefix}\n{notes}" if notes else prefix

        lead = InsuranceLead(
            organization_id=organization_id,
            contact_id=contact.id,
            assigned_agent_user_id=assigned_agent_user_id,
            source=source,
            status=status or "open",
            notes=lead_notes,
            related_policy_id=related_policy_id,
            demo_logged_at=demo_logged_at,
            followup_due_at=followup_due_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        await self.ensure_default_templates(organization_id)
        return lead

    async def start_lead_followup_workflow(
        self,
        *,
        lead_id: int,
        actor_user_id: int | None,
        followup_due_at: datetime | None = None,
        days_until_followup: int = 3,
    ) -> dict[str, object]:
        lead = await self._get_lead(lead_id)
        contact = await self.session.get(Contact, lead.contact_id)
        if contact is None:
            raise ValueError("lead contact not found")
        await self.ensure_default_templates(lead.organization_id)
        template = await self._ensure_workflow_template(
            organization_id=lead.organization_id,
            name="lead_followup_workflow",
            definition="demo + configurable follow-up delay",
        )
        # normalize followup date / compute naive UTC scheduled_for
        if followup_due_at is not None:
            followup_due_at = normalize_to_utc_naive(followup_due_at)
        scheduled_for = followup_due_at or (utcnow_naive() + timedelta(days=days_until_followup))
        title = f"Demo follow-up with {contact.name}" if lead.source == "demo" else f"Lead follow-up for {contact.name}"
        task = await self.task_service.create_task(
            organization_id=lead.organization_id,
            title=title,
            description=lead.notes,
            due_at=scheduled_for,
            domain="insurance",
            actor_user_id=actor_user_id,
        )
        if lead.assigned_agent_user_id is not None:
            await self.task_service.assign_task(
                task_id=task.id,
                organization_id=lead.organization_id,
                user_id=lead.assigned_agent_user_id,
                contact_id=None,
                actor_user_id=actor_user_id,
            )
        run = await self.workflow_service.start_workflow_run(
            organization_id=lead.organization_id,
            workflow_template_id=template.id,
            task_id=task.id,
            current_step="scheduled",
            actor_user_id=actor_user_id,
        )
        reminder = await self.reminder_service.create_reminder(
            organization_id=lead.organization_id,
            task_id=task.id,
            dedupe_key=f"lead-followup:{lead.id}",
            scheduled_for=scheduled_for,
            actor_user_id=actor_user_id,
        )
        await self.workflow_service.advance_workflow_state(
            run.id,
            current_step="scheduled",
            state_payload=json.dumps({"lead_id": lead.id, "task_id": task.id, "reminder_id": reminder.id}),
            actor_user_id=actor_user_id,
        )
        lead.status = "follow_up_pending"
        lead.followup_due_at = scheduled_for
        lead.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(lead)
        return {
            "lead": lead,
            "workflow_template": template,
            "workflow_run": run,
            "task": task,
            "reminder": reminder,
        }

    async def update_lead(self, lead_id: int, updates: dict, actor_user_id: int | None) -> InsuranceLead:
        lead = await self._get_lead(lead_id)
        next_status = updates.get("status")
        followup_due_at = updates.get("followup_due_at")
        # normalize followup_due_at if present
        if followup_due_at is not None:
            followup_due_at = normalize_to_utc_naive(followup_due_at)
            updates["followup_due_at"] = followup_due_at
        if (
            next_status is not None
            and next_status not in LEAD_FOLLOWUP_ACTION_STATUSES
            and next_status not in CLOSED_LEAD_STATUSES
            and next_status not in OPEN_LEAD_STATUSES
        ):
            raise ValueError(f"Unsupported lead status: {next_status}")
        for key, value in updates.items():
            setattr(lead, key, value)
        if next_status in CLOSED_LEAD_STATUSES:
            await self._close_lead_workflow(lead=lead, actor_user_id=actor_user_id)
        elif next_status == "follow_up_later" and followup_due_at is not None:
            await self._reschedule_lead_followup(lead=lead, followup_due_at=followup_due_at, actor_user_id=actor_user_id)
        lead.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def list_leads(self, organization_id: int, status: str | None = None) -> list[InsuranceLead]:
        query = select(InsuranceLead).where(InsuranceLead.organization_id == organization_id)
        if status is not None:
            query = query.where(InsuranceLead.status == status)
        result = await self.session.execute(query.order_by(InsuranceLead.created_at.desc()))
        return list(result.scalars())

    async def find_open_lead(self, *, organization_id: int, contact_name: str) -> InsuranceLead:
        result = await self.session.execute(
            select(Contact).where(
                Contact.organization_id == organization_id,
                Contact.name.ilike(f"%{contact_name}%"),
            )
        )
        contacts = list(result.scalars())
        if not contacts:
            raise ValueError("lead contact not found")
        contact_ids = [contact.id for contact in contacts]
        lead_result = await self.session.execute(
            select(InsuranceLead).where(
                InsuranceLead.organization_id == organization_id,
                InsuranceLead.contact_id.in_(contact_ids),
                InsuranceLead.status.in_(sorted(OPEN_LEAD_STATUSES)),
            )
        )
        leads = list(lead_result.scalars())
        if not leads:
            raise ValueError("lead not found")
        if len(leads) > 1:
            raise ValueError("multiple matching leads found")
        return leads[0]

    async def get_dashboard(self, organization_id: int) -> dict[str, object]:
        now = utcnow_naive()
        logger = logging.getLogger(__name__)
        from app.utils.policy_classifier import (
            classify_policy_summary_kpis,
            classify_ui_dashboard_kpis,
            days_until_utc,
            is_active_policy,
            is_critical_renewal,
            is_due_renewal,
        )

        policies = await self.list_policies(organization_id)
        leads = await self.list_leads(organization_id)

        kpis = classify_ui_dashboard_kpis(policies)
        policy_summary = classify_policy_summary_kpis(policies)
        from app.utils.lead_followup_classifier import classify_lead_followup_overview

        lead_followup_overview = classify_lead_followup_overview(leads)
        from app.utils.renewal_intelligence import build_renewal_intelligence_chart

        renewal_intelligence = await build_renewal_intelligence_chart(self.session, policies)
        grace_period_policies = [policy for policy in policies if is_grace_period(policy)]
        lapsed_policies = [policy for policy in policies if is_lapsed(policy)]
        active_policies = [policy for policy in policies if is_active_policy(policy)]
        due_renewals = [policy for policy in active_policies if is_due_renewal(policy)]
        expiring_policies = [policy for policy in active_policies if is_critical_renewal(policy)]
        pending_followups = [lead for lead in leads if lead.status in OPEN_LEAD_STATUSES and lead.followup_due_at is not None]
        today = now.date()
        due_followups = [
            lead
            for lead in leads
            if lead.status in OPEN_LEAD_STATUSES
            and lead.followup_due_at is not None
            and lead.followup_due_at.date() == today
        ]
        overdue_followups = [
            lead
            for lead in leads
            if lead.status in OPEN_LEAD_STATUSES
            and lead.followup_due_at is not None
            and lead.followup_due_at.date() < today
        ]

        for policy in policies:
            days_remaining = days_until_utc(policy.expiry_date)
            category = "unknown"
            if days_remaining is None:
                category = "unknown"
            elif days_remaining < 0:
                category = "grace_period_or_lapsed"
            elif 0 <= days_remaining <= 2:
                category = "expiring"
            elif 3 <= days_remaining <= 10:
                category = "due"
            elif days_remaining > 10:
                category = "active"
            logger.info(
                "[PolicyClassification] %s | expiry=%s | daysRemaining=%s | category=%s | assigned_agent=%s",
                policy.policy_number or "-",
                getattr(policy.expiry_date, "isoformat", lambda: str(policy.expiry_date))(),
                days_remaining,
                category,
                getattr(policy, "assigned_agent_user_id", None),
            )

        return {
            "expiring_policies": expiring_policies,
            "due_renewals": due_renewals,
            "upcoming_renewals": due_renewals,
            "grace_period_policies": grace_period_policies,
            "lapsed_policies": lapsed_policies,
            "pending_followups": pending_followups,
            "counts": {
                "total_policies": kpis["total_policies"],
                "active_policies": kpis["active_policies"],
                "expiring_policies": kpis["expiring_policies"],
                "due_renewals": kpis["due_renewals"],
                "upcoming_renewals": kpis["due_renewals"],
                "grace_period_policies": kpis["grace_period_policies"],
                "lapsed_policies": kpis["lapsed_policies"],
                "pending_followups": len(pending_followups),
                "due_followups": len(due_followups),
                "overdue_followups": len(overdue_followups),
            },
            "policy_summary": policy_summary,
            "lead_followup_overview": lead_followup_overview,
            "renewal_intelligence": renewal_intelligence,
        }

    async def get_ui_dashboard_kpis(self, organization_id: int) -> dict[str, int]:
        """KPI counts aligned with the Insurance Dashboard UI (insurance.tsx + policy-classifier)."""
        from app.utils.policy_classifier import classify_ui_dashboard_kpis

        logger = logging.getLogger(__name__)
        policies = await self.list_policies(organization_id)
        dashboard = await self.get_dashboard(organization_id)
        kpis = classify_ui_dashboard_kpis(policies)
        kpis["pending_followups"] = int(dashboard.get("counts", {}).get("pending_followups", 0))
        kpis["organization_id"] = organization_id

        logger.info(
            "[get_ui_dashboard_kpis] org=%s sql_policy_count=%s total=%s active=%s due=%s expiring=%s grace=%s lapsed=%s pending_followups=%s",
            organization_id,
            len(policies),
            kpis["total_policies"],
            kpis["active_policies"],
            kpis["due_renewals"],
            kpis["expiring_policies"],
            kpis["grace_period_policies"],
            kpis["lapsed_policies"],
            kpis["pending_followups"],
        )
        return kpis

    async def ensure_default_templates(self, organization_id: int) -> list[MessageTemplate]:
        result = await self.session.execute(
            select(MessageTemplate).where(MessageTemplate.organization_id == organization_id)
        )
        existing = {row.name: row for row in result.scalars()}
        created: list[MessageTemplate] = []
        now = utcnow_naive()
        for definition in INSURANCE_TEMPLATE_DEFINITIONS:
            if definition["name"] in existing:
                created.append(existing[definition["name"]])
                continue
            variables = sorted(extract_template_variables(definition["body"]))
            item = MessageTemplate(
                organization_id=organization_id,
                name=definition["name"],
                channel="whatsapp",
                purpose=definition["purpose"],
                status="approved",
                body=definition["body"],
                required_variables=variables,
                provider_template_name=None,
                approved_by_user_id=None,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(item)
            created.append(item)
        await self.session.commit()
        return created

    async def _resolve_logged_in_user_name(
        self,
        *,
        actor_user_id: int | None,
        explicit_name: str | None = None,
    ) -> str:
        if explicit_name and explicit_name.strip():
            return explicit_name.strip()
        if actor_user_id is None:
            return "SIMI Insurance"

        result = await self.session.execute(
            text("SELECT email FROM users WHERE id = :id"),
            {"id": int(actor_user_id)},
        )
        row = result.first()
        if row is None or not row.email:
            return "SIMI Insurance"
        return format_user_display_name(row.email)

    async def _resolve_contact(
        self,
        *,
        organization_id: int,
        name: str,
        allow_create: bool,
        phone: str | None = None,
        email: str | None = None,
    ) -> tuple[Contact, bool]:
        result = await self.session.execute(
            select(Contact).where(
                Contact.organization_id == organization_id,
                Contact.name.ilike(name),
            )
        )
        contact = result.scalar_one_or_none()
        if contact is not None:
            updated = False
            if phone and (contact.phone or "").strip() != phone.strip():
                contact.phone = phone.strip()
                updated = True
            if email and (contact.email or "").strip().lower() != email.strip().lower():
                contact.email = email.strip()
                updated = True
            if updated:
                contact.updated_at = utcnow_naive()
                await self.session.commit()
                await self.session.refresh(contact)
            return contact, False
        if not allow_create:
            raise ValueError("contact not found")
        now = utcnow_naive()
        contact = Contact(
            organization_id=organization_id,
            name=name,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(contact)
        await self.session.commit()
        await self.session.refresh(contact)
        return contact, True

    async def _ensure_notification_preference(self, *, organization_id: int, contact_id: int, preferred_channel: str) -> NotificationPreference:
        result = await self.session.execute(
            select(NotificationPreference).where(
                NotificationPreference.organization_id == organization_id,
                NotificationPreference.contact_id == contact_id,
                NotificationPreference.user_id.is_(None),
                NotificationPreference.purpose == "reminder",
            )
        )
        preference = result.scalar_one_or_none()
        now = utcnow_naive()
        if preference is None:
            preference = NotificationPreference(
                organization_id=organization_id,
                user_id=None,
                contact_id=contact_id,
                purpose="reminder",
                preferred_channel=preferred_channel,
                fallback_channel=None,
                opt_out=False,
                quiet_hours_start=None,
                quiet_hours_end=None,
                created_at=now,
                updated_at=now,
            )
            self.session.add(preference)
        else:
            preference.preferred_channel = preferred_channel
            preference.updated_at = now
        await self.session.commit()
        await self.session.refresh(preference)
        return preference

    async def _ensure_workflow_template(self, *, organization_id: int, name: str, definition: str) -> WorkflowTemplate:
        result = await self.session.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.organization_id == organization_id,
                WorkflowTemplate.name == name,
                WorkflowTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if template is not None:
            return template
        return await self.workflow_service.create_workflow_template(
            organization_id=organization_id,
            name=name,
            definition=definition,
        )

    async def _get_policy(self, policy_id: int) -> InsurancePolicy:
        result = await self.session.execute(
            select_insurance_policies(load_custom_reminders=True).where(
                InsurancePolicy.id == policy_id
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            raise ValueError("policy not found")
        return policy

    async def _refresh_policy_custom_reminders(self, policy: InsurancePolicy) -> InsurancePolicy:
        if policy.id is None:
            return policy
        result = await self.session.execute(
            select(PolicyCustomReminder)
            .where(PolicyCustomReminder.policy_id == policy.id)
            .order_by(PolicyCustomReminder.id)
        )
        rows = list(result.scalars().all())
        orm_attributes.set_committed_value(policy, "custom_reminders", rows)
        return policy

    def _parse_policy_dnd_pair(
        self,
        dnd_start_time: time | str | None,
        dnd_end_time: time | str | None,
    ) -> tuple[time | None, time | None]:
        return (
            parse_time_hhmm(dnd_start_time, field_name="dnd_start_time"),
            parse_time_hhmm(dnd_end_time, field_name="dnd_end_time"),
        )

    def _normalize_custom_reminders_payload(self, items: list | None) -> list[dict] | None:
        if items is None:
            return None
        return [CustomReminderSchema.model_validate(item).model_dump() for item in items]

    async def _replace_policy_custom_reminders(
        self,
        policy: InsurancePolicy,
        items: list[dict] | None,
        *,
        dnd_start_time: time | None = None,
        dnd_end_time: time | None = None,
    ) -> None:
        """DEPRECATED: new schedules use reminder_configs via PolicyGenericReminderService."""
        logger.info(
            "[custom_reminders] deprecated _replace_policy_custom_reminders policy_id=%s skipped",
            policy.id,
        )

    async def _load_policy_with_custom_reminders(self, policy_id: int) -> InsurancePolicy:
        return await self._get_policy(policy_id)

    async def _get_lead(self, lead_id: int) -> InsuranceLead:
        lead = await self.session.get(InsuranceLead, lead_id)
        if lead is None:
            raise ValueError("lead not found")
        return lead

    async def _cancel_renewal_policy_reminders(self, policy: InsurancePolicy) -> int:
        now = utcnow_naive()
        result = await self.session.execute(
            update(PolicyReminder)
            .where(
                PolicyReminder.policy_id == policy.id,
                func.lower(PolicyReminder.status).in_(["pending", "processing"]),
            )
            .values(status="CANCELED", updated_at=now)
        )
        legacy_cancelled = int(result.rowcount or 0)

        from app.services.reminder_instance_service import cancel_pending_reminder_instances

        generic_cancelled = await cancel_pending_reminder_instances(
            self.session,
            organization_id=policy.organization_id,
            entity_type="policy",
            entity_id=int(policy.id),
        )
        cancelled = legacy_cancelled + generic_cancelled
        logger.info(
            "[cancel_renewal_policy_reminders] policy_id=%s legacy_cancelled=%s generic_cancelled=%s",
            policy.id,
            legacy_cancelled,
            generic_cancelled,
        )
        return cancelled

    async def _cancel_core_renewal_reminders(self, policy: InsurancePolicy) -> int:
        now = utcnow_naive()
        reminders_to_cancel: list[Reminder] = []

        if hasattr(Reminder, "policy_id"):
            result = await self.session.execute(
                select(Reminder).where(
                    Reminder.organization_id == policy.organization_id,
                    Reminder.policy_id == policy.id,
                    Reminder.status.in_(["pending", "processing"]),
                    Reminder.scheduled_for > now,
                )
            )
            reminders_to_cancel = list(result.scalars())

        if not reminders_to_cancel:
            result = await self.session.execute(
                select(Reminder).where(
                    Reminder.organization_id == policy.organization_id,
                    Reminder.dedupe_key.like(f"renewal:{policy.id}:%"),
                    Reminder.status.in_(["pending", "processing"]),
                    Reminder.scheduled_for > now,
                )
            )
            reminders_to_cancel = list(result.scalars())

        if not reminders_to_cancel:
            runs = list(
                (
                    await self.session.execute(
                        select(WorkflowRun).where(WorkflowRun.organization_id == policy.organization_id)
                    )
                ).scalars()
            )
            task_ids: list[int] = []
            for run in runs:
                try:
                    payload = json.loads(run.state_payload or "{}")
                except json.JSONDecodeError:
                    continue
                if payload.get("policy_id") == policy.id:
                    tid = payload.get("task_id")
                    if tid is not None:
                        task_ids.append(tid)
            if task_ids:
                result = await self.session.execute(
                    select(Reminder).where(
                        Reminder.organization_id == policy.organization_id,
                        Reminder.task_id.in_(task_ids),
                        Reminder.status.in_(["pending", "processing"]),
                        Reminder.scheduled_for > now,
                    )
                )
                reminders_to_cancel = list(result.scalars())

        for reminder in reminders_to_cancel:
            reminder.status = "canceled"
            reminder.canceled_at = now
            reminder.updated_at = now
        return len(reminders_to_cancel)

    async def _send_renewal_confirmation(
        self,
        *,
        policy: InsurancePolicy,
        actor_user_id: int | None,
    ) -> tuple[bool, str | None]:
        contact = await self.session.get(Contact, policy.policyholder_id)
        if contact is None:
            return False, "policyholder contact not found"

        message = build_renewal_confirmation_message(
            customer_name=contact.name,
            policy_number=policy.policy_number,
        )
        channels = resolve_policy_reminder_channels(getattr(policy, "preferred_channel", None))
        channel = channels[0]
        try:
            return await send_policy_channel_message(
                self.session,
                organization_id=policy.organization_id,
                policy=policy,
                contact=contact,
                channel=channel,
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    async def _cancel_pending_policy_reminders(self, policy: InsurancePolicy) -> int:
        return await self._cancel_renewal_policy_reminders(policy)

    async def _complete_policy_workflow(
        self,
        *,
        policy: InsurancePolicy,
        actor_user_id: int | None,
    ) -> dict[str, int]:
        stats = {
            "cancelled_workflows": 0,
            "completed_tasks": 0,
            "cancelled_escalations": 0,
        }
        cancelled_escalation_ids: set[int] = set()
        result = await self.session.execute(
            select(WorkflowRun).where(WorkflowRun.organization_id == policy.organization_id)
        )
        runs = list(result.scalars())
        for run in runs:
            try:
                payload = json.loads(run.state_payload or "{}")
            except json.JSONDecodeError:
                continue
            if payload.get("policy_id") != policy.id:
                continue
            if run.status == "running":
                await self.workflow_service.cancel_workflow(run.id, actor_user_id=actor_user_id)
                stats["cancelled_workflows"] += 1
            task_id = payload.get("task_id")
            escalation_task_id = payload.get("escalation_task_id")
            if task_id is not None:
                await self.task_service.complete_task(task_id, actor_user_id=actor_user_id, cancel_future_reminders=True)
                stats["completed_tasks"] += 1
            if escalation_task_id is not None:
                await self.task_service.cancel_task(escalation_task_id, actor_user_id=actor_user_id)
                cancelled_escalation_ids.add(int(escalation_task_id))
                stats["cancelled_escalations"] += 1

        open_escalation = await self._find_open_escalation_task(policy)
        if open_escalation is not None and open_escalation.id not in cancelled_escalation_ids:
            await self.task_service.cancel_task(open_escalation.id, actor_user_id=actor_user_id)
            stats["cancelled_escalations"] += 1
        return stats

    async def _close_lead_workflow(self, *, lead: InsuranceLead, actor_user_id: int | None) -> None:
        result = await self.session.execute(select(WorkflowRun).where(WorkflowRun.organization_id == lead.organization_id))
        runs = list(result.scalars())
        for run in runs:
            try:
                payload = json.loads(run.state_payload or "{}")
            except json.JSONDecodeError:
                continue
            if payload.get("lead_id") != lead.id:
                continue
            task_id = payload.get("task_id")
            if run.status == "running":
                await self.workflow_service.complete_workflow(run.id, actor_user_id=actor_user_id)
            if task_id is not None:
                await self.task_service.complete_task(task_id, actor_user_id=actor_user_id, cancel_future_reminders=True)

    async def _reschedule_lead_followup(self, *, lead: InsuranceLead, followup_due_at: datetime, actor_user_id: int | None) -> None:
        followup_due_at = normalize_to_utc_naive(followup_due_at)
        result = await self.session.execute(select(WorkflowRun).where(WorkflowRun.organization_id == lead.organization_id))
        runs = list(result.scalars())
        for run in runs:
            try:
                payload = json.loads(run.state_payload or "{}")
            except json.JSONDecodeError:
                continue
            if payload.get("lead_id") != lead.id:
                continue
            task_id = payload.get("task_id")
            reminder_id = payload.get("reminder_id")
            if task_id is not None:
                task = await self.session.get(Task, task_id)
                if task is not None:
                    task.due_at = followup_due_at
                    task.status = "snoozed"
                    task.updated_at = utcnow_naive()
            if reminder_id is not None:
                reminder = await self.reminder_service.snooze_reminder(reminder_id, followup_due_at, actor_user_id=actor_user_id)
                payload["reminder_id"] = reminder.id
            await self.workflow_service.advance_workflow_state(
                run.id,
                current_step="rescheduled",
                state_payload=json.dumps(payload),
                actor_user_id=actor_user_id,
            )
        lead.followup_due_at = followup_due_at

    def _generate_policy_number(self, organization_id: int, contact_id: int) -> str:
        return f"POL-{organization_id}-{contact_id}-{int(utcnow_naive().timestamp())}"
