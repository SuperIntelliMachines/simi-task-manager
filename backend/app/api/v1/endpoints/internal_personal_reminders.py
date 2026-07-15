"""Internal scheduler endpoints for Personal Reminder processing."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.reminder import ReminderProcessResponse
from app.services.personal_reminder_processor import PersonalReminderProcessorService

router = APIRouter(prefix="/internal/personal-reminders", tags=["internal-personal-reminders"])


async def require_scheduler_secret(
    x_scheduler_secret: str | None = Header(default=None, alias="X-Scheduler-Secret"),
) -> None:
    settings = get_settings()
    expected = settings.scheduler_secret
    provided = x_scheduler_secret or ""
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid scheduler secret")


@router.post("/process", response_model=ReminderProcessResponse)
async def process_personal_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_scheduler_secret),
) -> ReminderProcessResponse:
    service = PersonalReminderProcessorService(session)
    result = await service.process_due_reminders()
    return ReminderProcessResponse(**result)
