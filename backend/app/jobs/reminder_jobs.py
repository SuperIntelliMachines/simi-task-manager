from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import NotificationPreference, OutboundMessage
from app.models.core import Contact, Reminder, ReminderAttempt, Task, TaskAssignment
from app.models.verticals import InsuranceLead
from app.services.audit_service import write_audit_event
from app.services.channel_adapter import get_channel_adapter
from app.services.insurance_messaging import (
    LEAD_FOLLOWUP_DEDUPE_PREFIX,
    parse_lead_id_from_dedupe_key,
    resolve_lead_policy_type,
    send_lead_followup_agent_reminder,
)
from app.services.insurance_service import build_agent_follow_up_message
from app.utils.datetime_utils import normalize_to_utc_naive

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _count_overdue_follow_up_pending_leads(session: AsyncSession) -> int:
    """Diagnostic only — leads the UI marks overdue; not queried by the job."""
    now = utcnow_naive()
    result = await session.execute(
        select(func.count())
        .select_from(InsuranceLead)
        .where(
            func.lower(InsuranceLead.status) == "follow_up_pending",
            InsuranceLead.followup_due_at.is_not(None),
            InsuranceLead.followup_due_at <= now,
        )
    )
    return int(result.scalar_one() or 0)


async def _count_due_lead_reminders(
    session: AsyncSession,
    *,
    organization_id: int | None = None,
) -> int:
    now = utcnow_naive()
    stmt = (
        select(func.count())
        .select_from(Reminder)
        .where(
            Reminder.status == "pending",
            Reminder.scheduled_for <= now,
            Reminder.dedupe_key.like(f"{LEAD_FOLLOWUP_DEDUPE_PREFIX}%"),
        )
    )
    if organization_id is not None:
        stmt = stmt.where(Reminder.organization_id == organization_id)
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def _log_lead_reminder_diagnostics(
    session: AsyncSession,
    *,
    organization_id: int | None,
    phase: str,
    **extra: object,
) -> None:
    overdue_leads = await _count_overdue_follow_up_pending_leads(session)
    due_lead_reminders = await _count_due_lead_reminders(session, organization_id=organization_id)
    logger.info(
        "[LeadReminderJob] phase=%s org_id=%s overdue_follow_up_pending_leads=%s "
        "due_lead_reminders_in_reminders_table=%s %s",
        phase,
        organization_id,
        overdue_leads,
        due_lead_reminders,
        " ".join(f"{key}={value}" for key, value in extra.items()),
    )
    if overdue_leads > 0 and due_lead_reminders == 0:
        logger.warning(
            "[LeadReminderJob] overdue leads exist in insurance_leads but no due rows in "
            "reminders (status=pending, scheduled_for<=now, dedupe_key=lead-followup:*). "
            "Ensure start_lead_followup_workflow was called for each lead."
        )


async def _send_generic_reminder(
    session: AsyncSession,
    *,
    organization_id: int,
    reminder_id: int,
    task_id: int,
    adapter,
) -> tuple[bool, str | None, str, str, str | None]:
    task = await session.get(Task, task_id)
    recipient = "tenant-admin"
    selected_channel = "whatsapp"
    body = f"Reminder for task #{task_id}"
    if task is not None:
        body = f"Reminder: {task.title}"

        assignment_result = await session.execute(
            select(TaskAssignment).where(TaskAssignment.task_id == task.id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if assignment is not None:
            pref_result = await session.execute(
                select(NotificationPreference).where(
                    NotificationPreference.organization_id == organization_id,
                    NotificationPreference.contact_id == assignment.contact_id,
                    NotificationPreference.user_id == assignment.user_id,
                    NotificationPreference.purpose == "reminder",
                )
            )
            pref = pref_result.scalar_one_or_none()
            if pref is not None and not pref.opt_out:
                selected_channel = pref.preferred_channel
            elif pref is not None and pref.opt_out:
                return False, "recipient opted out", selected_channel, body, None

    provider_id = await adapter.send_message(
        channel=selected_channel,
        recipient=recipient,
        body=body,
    )
    session.add(
        OutboundMessage(
            organization_id=organization_id,
            task_id=task_id,
            channel=selected_channel,
            recipient=recipient,
            body=body,
            external_provider_message_id=provider_id,
            status="sent",
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
    )
    return True, None, selected_channel, body, provider_id


async def _send_lead_followup_reminder(
    session: AsyncSession,
    *,
    organization_id: int,
    task_id: int,
    lead_id: int,
) -> tuple[bool, str | None, str, str | None]:
    lead = await session.get(InsuranceLead, lead_id)
    if lead is None:
        return False, "lead not found", "", None

    contact = await session.get(Contact, lead.contact_id)
    customer_name = contact.name if contact is not None else "the customer"
    policy_type = await resolve_lead_policy_type(session, lead)
    message = build_agent_follow_up_message(
        customer_name=customer_name,
        policy_type=policy_type,
    )
    return await send_lead_followup_agent_reminder(
        session,
        organization_id=organization_id,
        lead_id=lead_id,
        task_id=task_id,
        message=message,
    )


async def process_due_reminders(session: AsyncSession, organization_id: int) -> int:
    now = utcnow_naive()
    await _log_lead_reminder_diagnostics(session, organization_id=organization_id, phase="org_start")

    result = await session.execute(
        select(Reminder)
        .where(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.scheduled_for <= now,
        )
        .with_for_update(skip_locked=True)
    )
    reminders = list(result.scalars())
    due_lead_reminders = [r for r in reminders if (r.dedupe_key or "").startswith(LEAD_FOLLOWUP_DEDUPE_PREFIX)]
    due_other_reminders = len(reminders) - len(due_lead_reminders)

    logger.info(
        "[LeadReminderJob] org_id=%s due_reminders_total=%s due_lead_followup_reminders=%s due_other_reminders=%s",
        organization_id,
        len(reminders),
        len(due_lead_reminders),
        due_other_reminders,
    )

    pending_reminders = [
        (reminder.id, reminder.dedupe_key, reminder.task_id) for reminder in reminders
    ]
    adapter = get_channel_adapter()
    processed = 0
    skipped: dict[str, int] = {
        "reminder_missing": 0,
        "opted_out": 0,
        "send_failed": 0,
    }

    for reminder_id, dedupe_key, task_id in pending_reminders:
        reminder = await session.get(Reminder, reminder_id)
        if reminder is None:
            skipped["reminder_missing"] += 1
            logger.info(
                "[LeadReminderJob] reminder_id=%s skipped reason=reminder_missing_after_lock",
                reminder_id,
            )
            continue

        lead_id = parse_lead_id_from_dedupe_key(dedupe_key)
        if lead_id is not None:
            lead = await session.get(InsuranceLead, lead_id)
            lead_status = getattr(lead, "status", None) if lead is not None else None
            lead_followup_due_at = (
                normalize_to_utc_naive(lead.followup_due_at)
                if lead is not None and lead.followup_due_at is not None
                else None
            )
            logger.info(
                "[LeadReminderJob] examining reminder_id=%s lead_id=%s lead_status=%s "
                "lead_followup_due_at=%s reminder_scheduled_for=%s reminder_status=%s",
                reminder_id,
                lead_id,
                lead_status,
                lead_followup_due_at.isoformat() if lead_followup_due_at else None,
                reminder.scheduled_for.isoformat() if reminder.scheduled_for else None,
                reminder.status,
            )
        else:
            logger.info(
                "[LeadReminderJob] examining reminder_id=%s dedupe_key=%s (non-lead reminder)",
                reminder_id,
                dedupe_key,
            )

        reminder.status = "processing"
        reminder.updated_at = now
        await session.flush()

        sent_at = utcnow_naive()
        channel = ""
        send_result = "failed"
        provider_id: str | None = None
        error: str | None = None
        success = False

        try:
            if lead_id is not None:
                success, error, channel, _recipient = await _send_lead_followup_reminder(
                    session,
                    organization_id=organization_id,
                    task_id=task_id,
                    lead_id=lead_id,
                )
                if success:
                    send_result = "sent"
                else:
                    send_result = f"failed: {error}"
            else:
                success, error, channel, _body, provider_id = await _send_generic_reminder(
                    session,
                    organization_id=organization_id,
                    reminder_id=reminder_id,
                    task_id=task_id,
                    adapter=adapter,
                )
                if success:
                    send_result = "sent"
                elif error == "recipient opted out":
                    send_result = "canceled"
                else:
                    send_result = f"failed: {error}"

            reminder = await session.get(Reminder, reminder_id)
            if reminder is None:
                skipped["reminder_missing"] += 1
                continue

            if error == "recipient opted out":
                reminder.status = "canceled"
                reminder.canceled_at = utcnow_naive()
                reminder.updated_at = utcnow_naive()
                skipped["opted_out"] += 1
                logger.info(
                    "[LeadReminderJob] reminder_id=%s lead_id=%s skipped reason=opted_out",
                    reminder_id,
                    lead_id,
                )
            elif success:
                reminder.status = "sent"
                reminder.sent_at = sent_at
                reminder.updated_at = sent_at
                processed += 1

                await write_audit_event(
                    session=session,
                    organization_id=organization_id,
                    actor_user_id=None,
                    event_type="reminder.sent",
                    entity_type="reminder",
                    entity_id=str(reminder_id),
                    payload={
                        "provider_message_id": provider_id,
                        "lead_id": lead_id,
                        "channel": channel,
                        "template": "agent_follow_up" if lead_id is not None else "generic",
                    },
                )
                logger.info(
                    "[LeadReminderJob] reminder_id=%s lead_id=%s processed=1 channel=%s",
                    reminder_id,
                    lead_id,
                    channel or "-",
                )
            else:
                raise RuntimeError(error or "send failed")
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            reminder = await session.get(Reminder, reminder_id)
            if reminder is None:
                skipped["reminder_missing"] += 1
                continue
            attempt_result = await session.execute(
                select(ReminderAttempt).where(ReminderAttempt.reminder_id == reminder_id)
            )
            attempts = list(attempt_result.scalars())
            next_number = len(attempts) + 1
            session.add(
                ReminderAttempt(
                    organization_id=organization_id,
                    reminder_id=reminder_id,
                    attempt_number=next_number,
                    status="failed",
                    error_message=str(exc),
                    next_retry_at=utcnow_naive() + timedelta(minutes=5),
                    created_at=utcnow_naive(),
                    updated_at=utcnow_naive(),
                )
            )
            reminder.status = "pending"
            reminder.updated_at = utcnow_naive()
            send_result = f"failed: {exc}"
            error = str(exc)
            skipped["send_failed"] += 1
            logger.warning(
                "[LeadReminderJob] reminder_id=%s lead_id=%s skipped reason=send_failed error=%s",
                reminder_id,
                lead_id,
                error,
            )

        if lead_id is not None:
            logger.info(
                "[LeadFollowupReminder] lead_id=%s reminder_id=%s channel=%s send_result=%s",
                lead_id,
                reminder_id,
                channel or "-",
                send_result,
            )

    await session.commit()
    logger.info(
        "[LeadReminderJob] org_id=%s processed=%s skipped=%s",
        organization_id,
        processed,
        skipped,
    )
    await _log_lead_reminder_diagnostics(
        session,
        organization_id=organization_id,
        phase="org_complete",
        processed=processed,
        skipped=skipped,
    )
    return processed


async def process_due_reminders_all(session: AsyncSession) -> int:
    await _log_lead_reminder_diagnostics(session, organization_id=None, phase="job_start")

    now = utcnow_naive()
    result = await session.execute(
        select(Reminder.organization_id)
        .where(
            Reminder.status == "pending",
            Reminder.scheduled_for <= now,
        )
        .distinct()
    )
    org_ids = list(result.scalars())
    logger.info(
        "[LeadReminderJob] job_start due_reminder_orgs=%s org_ids=%s",
        len(org_ids),
        org_ids,
    )

    if not org_ids:
        logger.info(
            "[LeadReminderJob] job_complete processed=0 reason=no_orgs_with_due_pending_reminders "
            "(queries reminders table, not insurance_leads)"
        )
        await _log_lead_reminder_diagnostics(session, organization_id=None, phase="job_complete", processed=0)
        return 0

    total = 0
    for org_id in org_ids:
        total += await process_due_reminders(session, org_id)

    logger.info("[LeadReminderJob] job_complete processed=%s orgs=%s", total, len(org_ids))
    await _log_lead_reminder_diagnostics(session, organization_id=None, phase="job_complete", processed=total)
    return total


async def retry_failed_reminder_attempts(session: AsyncSession, organization_id: int) -> int:
    now = utcnow_naive()
    result = await session.execute(
        select(ReminderAttempt).where(
            ReminderAttempt.organization_id == organization_id,
            ReminderAttempt.status == "failed",
            ReminderAttempt.next_retry_at.is_not(None),
            ReminderAttempt.next_retry_at <= now,
        )
    )
    attempts = list(result.scalars())

    retried = 0
    for attempt in attempts:
        reminder = await session.get(Reminder, attempt.reminder_id)
        if reminder is None:
            continue
        reminder.status = "pending"
        reminder.updated_at = utcnow_naive()
        attempt.status = "retried"
        attempt.updated_at = utcnow_naive()
        retried += 1

    await session.commit()
    return retried


async def escalate_overdue_tasks(session: AsyncSession, organization_id: int) -> int:
    now = utcnow_naive()
    result = await session.execute(
        select(Task).where(
            Task.organization_id == organization_id,
            Task.status.in_(["open", "snoozed"]),
            Task.due_at.is_not(None),
            Task.due_at < now,
        )
    )
    rows = list(result.scalars())

    for task in rows:
        await write_audit_event(
            session=session,
            organization_id=organization_id,
            actor_user_id=None,
            event_type="task.escalated",
            entity_type="task",
            entity_id=str(task.id),
            payload={"reason": "overdue"},
        )

    await session.commit()
    return len(rows)
