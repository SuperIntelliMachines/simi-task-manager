from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.jobs.policy_reminder_generator import repair_personalized_policy_reminder_schedules_all
from app.jobs.personal_reminder_jobs import process_due_personal_reminders
from app.jobs.reminder_engine_jobs import (
    generate_reminder_instances_all,
    process_due_reminder_instances_all,
    run_reminder_engine_cycle,
)
from app.jobs.reminder_jobs import process_due_reminders_all
from app.jobs.renewal_escalation_jobs import process_renewal_escalations_all
from app.schemas.reminder import ReminderProcessResponse
from app.schemas.scheduler_jobs import (
    RenewalEscalationJobResponse,
    RepairPolicyRemindersResponse,
    SchedulerJobCountResponse,
    SchedulerSuccessResponse,
)

router = APIRouter(prefix="/internal/jobs", tags=["scheduler-jobs"])


async def require_scheduler_secret(
    x_scheduler_secret: str | None = Header(default=None, alias="X-Scheduler-Secret"),
) -> None:
    settings = get_settings()
    expected = settings.scheduler_secret
    provided = x_scheduler_secret or ""
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid scheduler secret")


@router.post("/process-lead-reminders", response_model=SchedulerJobCountResponse)
async def process_lead_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> SchedulerJobCountResponse:
    processed = await process_due_reminders_all(session)
    return SchedulerJobCountResponse(processed=processed)


@router.post(
    "/process-personal-reminders",
    response_model=ReminderProcessResponse,
    summary="Process due personal reminders",
    description="Send due PENDING personal reminders via ChannelService.",
)
async def process_personal_reminders_job(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> ReminderProcessResponse:
    stats = await process_due_personal_reminders(session)
    return ReminderProcessResponse(**stats)


@router.post(
    "/process-policy-reminders",
    response_model=SchedulerJobCountResponse,
    summary="Process due policy reminders",
    description="Send messages for existing PENDING policy reminders whose reminder_at is due.",
)
async def process_policy_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> SchedulerJobCountResponse:
    stats = await process_due_reminder_instances_all(session)
    return SchedulerJobCountResponse(
        processed=int(stats.get("processed", 0)),
        fetched=int(stats.get("processed", 0)),
        failed=int(stats.get("failed", 0)),
        due_total=int(stats.get("processed", 0)),
    )


@router.post(
    "/generate-policy-reminders",
    response_model=SchedulerSuccessResponse,
    summary="Generate policy reminder rows",
    description=(
        "Create policy_reminders rows for eligible policies only. "
        "Does not send messages or mark reminders SENT."
    ),
)
async def generate_policy_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> SchedulerSuccessResponse:
    """Generate reminder_instances from active reminder_configs (all entity types)."""
    await generate_reminder_instances_all(session)
    return SchedulerSuccessResponse()


@router.post(
    "/repair-policy-reminders",
    response_model=RepairPolicyRemindersResponse,
    summary="Repair personalized policy reminder schedules",
    description=(
        "Delete stale PENDING personalized policy_reminders rows (wrong or duplicate "
        "reminder_at) and regenerate UTC-correct per-stage schedule rows."
    ),
)
async def repair_policy_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> RepairPolicyRemindersResponse:
    stats = await repair_personalized_policy_reminder_schedules_all(session)
    return RepairPolicyRemindersResponse(**stats)


@router.post(
    "/policy-reminder-cycle",
    response_model=SchedulerSuccessResponse,
    summary="Generate and process policy reminders",
    description="Production cycle: generate reminder rows, then send all due PENDING reminders.",
)
async def policy_reminder_cycle(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> SchedulerSuccessResponse:
    await run_reminder_engine_cycle(session)
    return SchedulerSuccessResponse()


@router.post(
    "/reminder-engine-cycle",
    response_model=SchedulerSuccessResponse,
    summary="Generate and process all reminder engine instances",
    description="Generic cycle: generate reminder_instances from configs, then process due sends.",
)
async def reminder_engine_cycle(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> SchedulerSuccessResponse:
    await run_reminder_engine_cycle(session)
    return SchedulerSuccessResponse()


@router.post(
    "/process-renewal-escalations",
    response_model=RenewalEscalationJobResponse,
    summary="Process expired policy renewal escalations",
    description=(
        "Find policies with expiry before today that are not renewed or escalated, "
        "create escalation tasks for assigned agents, email agents, and set status to escalated. "
        "Idempotent — safe to run daily (recommended: 1:00 AM via Cloud Scheduler)."
    ),
)
async def process_renewal_escalations(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> RenewalEscalationJobResponse:
    stats = await process_renewal_escalations_all(session)
    return RenewalEscalationJobResponse(**stats)
