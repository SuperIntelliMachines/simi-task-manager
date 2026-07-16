"""Reminder History read APIs (Reminder Management)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, PermissionChecker, get_current_user
from app.core.database import get_db_session
from app.core.permissions import REMINDERS_VIEW
from app.models.reminder_history import ReminderHistory
from app.schemas.reminder_history import (
    ReminderHistoryDetailResponse,
    ReminderHistoryListItem,
    ReminderHistoryListResponse,
    ReminderHistoryReminderSummary,
    ReminderHistoryTemplateSummary,
)
from app.services.reminder_history_query_service import ReminderHistoryQueryService

router = APIRouter(
    prefix="/reminder-history",
    tags=["reminder-history"],
    dependencies=[Depends(get_current_user)],
)


def _strip_tz(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _serialize_list_item(row: ReminderHistory) -> ReminderHistoryListItem:
    return ReminderHistoryListItem(
        id=row.id,
        organization_id=int(row.organization_id),
        reminder_id=row.reminder_id,
        template_id=row.template_id,
        created_by=int(row.created_by),
        reminder_title=row.reminder_title,
        channel=row.channel,
        recipient=row.recipient,
        status=row.status,
        provider_message_id=row.provider_message_id,
        error_message=row.error_message,
        executed_at=row.executed_at,
    )


@router.get(
    "",
    response_model=ReminderHistoryListResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_reminder_history(
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    organization_id: int | None = Query(
        default=None,
        description="Must match the caller's organization when provided.",
    ),
    executed_from: datetime | None = Query(default=None),
    executed_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None, description="Search title or recipient"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderHistoryListResponse:
    if organization_id is not None and int(organization_id) != int(current_user.organization_id):
        raise HTTPException(status_code=403, detail="organization_id does not match current organization")

    service = ReminderHistoryQueryService(session)
    items, total = await service.list_history(
        organization_id=current_user.organization_id,
        status=(status or "").strip() or None,
        channel=(channel or "").strip() or None,
        executed_from=_strip_tz(executed_from),
        executed_to=_strip_tz(executed_to),
        search=(search or "").strip() or None,
        page=page,
        page_size=page_size,
    )
    return ReminderHistoryListResponse(
        items=[_serialize_list_item(row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{history_id}",
    response_model=ReminderHistoryDetailResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def get_reminder_history(
    history_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderHistoryDetailResponse:
    service = ReminderHistoryQueryService(session)
    try:
        row = await service.get_history(
            organization_id=current_user.organization_id,
            history_id=history_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    reminder = await service.load_reminder(
        organization_id=current_user.organization_id,
        reminder_id=row.reminder_id,
    )
    template = await service.load_template(
        organization_id=current_user.organization_id,
        template_id=row.template_id,
    )

    return ReminderHistoryDetailResponse(
        id=row.id,
        organization_id=int(row.organization_id),
        reminder_id=row.reminder_id,
        template_id=row.template_id,
        created_by=int(row.created_by),
        reminder_title=row.reminder_title,
        channel=row.channel,
        recipient=row.recipient,
        status=row.status,
        provider_message_id=row.provider_message_id,
        error_message=row.error_message,
        executed_at=row.executed_at,
        created_at=row.created_at,
        reminder=(
            ReminderHistoryReminderSummary(
                id=reminder.id,
                title=reminder.title,
                status=reminder.status,
                scheduled_at=reminder.scheduled_at,
                is_active=bool(reminder.is_active),
            )
            if reminder is not None
            else None
        ),
        template=(
            ReminderHistoryTemplateSummary(
                id=template.id,
                name=template.name,
                channel=template.channel,
                is_active=bool(template.is_active),
            )
            if template is not None
            else None
        ),
    )
