from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.reminder import (
    ReminderGenerateAllBody,
    ReminderGenerateBody,
    ReminderGenerateResponse,
    ReminderProcessBody,
    ReminderProcessResponse,
)
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_processor import ReminderProcessorService

router = APIRouter(prefix="/internal/reminders", tags=["internal-reminders"])


async def require_scheduler_secret(
    x_scheduler_secret: str | None = Header(default=None, alias="X-Scheduler-Secret"),
) -> None:
    settings = get_settings()
    expected = settings.scheduler_secret
    provided = x_scheduler_secret or ""
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid scheduler secret")


@router.post("/generate", response_model=ReminderGenerateResponse)
async def generate_reminders(
    body: ReminderGenerateBody,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> ReminderGenerateResponse:
    service = ReminderGeneratorService(session)

    if body.entity_type is None and body.entity_id is None and body.anchor_date is None:
        created = await service.generate_from_active_configs(organization_id=body.organization_id)
        return ReminderGenerateResponse(generated=len(created))

    if body.entity_type is None or body.entity_id is None or body.anchor_date is None:
        raise HTTPException(
            status_code=422,
            detail="entity_type, entity_id, and anchor_date are required for single-entity generation",
        )

    created = await service.generate_instances(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        organization_id=body.organization_id,
        anchor_date=body.anchor_date,
    )
    return ReminderGenerateResponse(generated=len(created))


@router.post("/generate-all", response_model=ReminderGenerateResponse)
async def generate_all_reminders(
    body: ReminderGenerateAllBody,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> ReminderGenerateResponse:
    service = ReminderGeneratorService(session)
    created = await service.generate_from_active_configs(organization_id=body.organization_id)
    return ReminderGenerateResponse(generated=len(created))


@router.post("/process", response_model=ReminderProcessResponse)
async def process_reminders(
    body: ReminderProcessBody,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> ReminderProcessResponse:
    service = ReminderProcessorService(session)
    result = await service.process_due_reminders(body.organization_id)
    return ReminderProcessResponse(**result)
