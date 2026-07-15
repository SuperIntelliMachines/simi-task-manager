"""Personal Reminder CRUD APIs (independent of the Generic Reminder Engine)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, PermissionChecker, get_current_user
from app.core.database import get_db_session
from app.core.permissions import (
    REMINDERS_CREATE,
    REMINDERS_DELETE,
    REMINDERS_UPDATE,
    REMINDERS_VIEW,
)
from app.models.personal_reminder import PersonalReminder
from app.schemas.personal_reminder import (
    PersonalReminderCreate,
    PersonalReminderListResponse,
    PersonalReminderResponse,
    PersonalReminderUpdate,
)
from app.services.personal_reminder_service import PersonalReminderService

router = APIRouter(
    prefix="/personal-reminders",
    tags=["personal-reminders"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(row: PersonalReminder) -> PersonalReminderResponse:
    return PersonalReminderResponse(
        id=row.id,
        organization_id=int(row.organization_id),
        created_by=int(row.created_by),
        title=row.title,
        description=row.description,
        scheduled_at=row.scheduled_at,
        channels=list(row.channels or []),
        email=row.email,
        mobile_number=row.mobile_number,
        whatsapp_number=row.whatsapp_number,
        telegram_chat_id=row.telegram_chat_id,
        template_id=row.template_id,
        custom_message=row.custom_message,
        status=row.status,
        sent_at=row.sent_at,
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "",
    response_model=PersonalReminderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(REMINDERS_CREATE))],
)
async def create_personal_reminder(
    body: PersonalReminderCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PersonalReminderResponse:
    service = PersonalReminderService(session)
    row = await service.create_reminder(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        payload=body,
    )
    await session.commit()
    return _serialize(row)


@router.get(
    "",
    response_model=PersonalReminderListResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_personal_reminders(
    status_filter: str | None = Query(default=None, alias="status"),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Search title or description"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PersonalReminderListResponse:
    service = PersonalReminderService(session)
    items, total = await service.list_reminders(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        status=(status_filter or "").strip() or None,
        is_active=is_active,
        q=(q or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return PersonalReminderListResponse(
        items=[_serialize(row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{reminder_id}",
    response_model=PersonalReminderResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def get_personal_reminder(
    reminder_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PersonalReminderResponse:
    service = PersonalReminderService(session)
    try:
        row = await service.get_reminder(
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            reminder_id=reminder_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)


@router.put(
    "/{reminder_id}",
    response_model=PersonalReminderResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_UPDATE))],
)
async def update_personal_reminder(
    reminder_id: uuid.UUID,
    body: PersonalReminderUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PersonalReminderResponse:
    service = PersonalReminderService(session)
    try:
        row = await service.update_reminder(
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            reminder_id=reminder_id,
            payload=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _serialize(row)


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(PermissionChecker(REMINDERS_DELETE))],
)
async def delete_personal_reminder(
    reminder_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    service = PersonalReminderService(session)
    try:
        await service.delete_reminder(
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            reminder_id=reminder_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
