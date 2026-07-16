"""General Reminder Definition CRUD APIs (platform feature).

Stores reminder definitions only — no generation, notification, or module coupling.
"""

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
from app.models.reminder_definition import ReminderDefinition
from app.schemas.general_reminder import (
    GeneralReminderCreateRequest,
    GeneralReminderListResponse,
    GeneralReminderResponse,
    GeneralReminderUpdateRequest,
    RecurrencePayload,
    SchedulePayload,
    TriggerPayload,
)
from app.services.reminder_definition_service import ReminderDefinitionService

router = APIRouter(
    prefix="/general-reminders",
    tags=["general-reminders"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(row: ReminderDefinition) -> GeneralReminderResponse:
    return GeneralReminderResponse(
        id=row.id,
        organization_id=int(row.organization_id),
        module_key=row.module_key,
        reminder_name=row.reminder_name,
        description=row.description,
        trigger=TriggerPayload(type=row.trigger_type, key=row.trigger_key),
        schedule=SchedulePayload(
            offset_value=int(row.offset_value),
            offset_unit=row.offset_unit,
            direction=row.offset_direction,
        ),
        recurrence=RecurrencePayload(
            repeat_enabled=bool(getattr(row, "repeat_enabled", False)),
            repeat_frequency_value=getattr(row, "repeat_frequency_value", None),
            repeat_frequency_unit=getattr(row, "repeat_frequency_unit", None),
            max_attempts=getattr(row, "max_attempts", None),
            stop_condition=getattr(row, "stop_condition", "entity_ineligible"),
            stop_condition_config=getattr(row, "stop_condition_config", None),
        ),
        channels=list(row.channels or []),
        template_key=row.template_key,
        is_active=bool(row.is_active),
        created_by=int(row.created_by) if row.created_by is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "",
    response_model=GeneralReminderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(REMINDERS_CREATE))],
)
async def create_general_reminder(
    body: GeneralReminderCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeneralReminderResponse:
    service = ReminderDefinitionService(session)
    row = await service.create(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        payload=body,
    )
    await session.commit()
    return _serialize(row)


@router.get(
    "",
    response_model=GeneralReminderListResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_general_reminders(
    module_key: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    trigger_type: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search name, description, module_key, trigger_key"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeneralReminderListResponse:
    service = ReminderDefinitionService(session)
    items, total = await service.list(
        organization_id=current_user.organization_id,
        module_key=(module_key or "").strip() or None,
        is_active=is_active,
        trigger_type=(trigger_type or "").strip().lower() or None,
        q=(q or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return GeneralReminderListResponse(
        items=[_serialize(row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{definition_id}",
    response_model=GeneralReminderResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def get_general_reminder(
    definition_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeneralReminderResponse:
    service = ReminderDefinitionService(session)
    try:
        row = await service.get(
            organization_id=current_user.organization_id,
            definition_id=definition_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)


@router.put(
    "/{definition_id}",
    response_model=GeneralReminderResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_UPDATE))],
)
async def update_general_reminder(
    definition_id: uuid.UUID,
    body: GeneralReminderUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeneralReminderResponse:
    service = ReminderDefinitionService(session)
    try:
        row = await service.update(
            organization_id=current_user.organization_id,
            definition_id=definition_id,
            payload=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _serialize(row)


@router.delete(
    "/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(PermissionChecker(REMINDERS_DELETE))],
)
async def delete_general_reminder(
    definition_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    service = ReminderDefinitionService(session)
    try:
        await service.delete(
            organization_id=current_user.organization_id,
            definition_id=definition_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
