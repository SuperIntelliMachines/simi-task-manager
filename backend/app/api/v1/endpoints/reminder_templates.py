"""Reminder Template CRUD APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, PermissionChecker, get_current_user
from app.core.database import get_db_session
from app.core.permissions import (
    TEMPLATES_CREATE,
    TEMPLATES_UPDATE,
    TEMPLATES_VIEW,
)
from app.models.reminder_template import ReminderTemplate
from app.schemas.reminder_template import (
    ReminderTemplateCreate,
    ReminderTemplateListResponse,
    ReminderTemplateResponse,
    ReminderTemplateUpdate,
)
from app.services.reminder_template_service import ReminderTemplateService

router = APIRouter(
    prefix="/reminder-templates",
    tags=["reminder-templates"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(row: ReminderTemplate) -> ReminderTemplateResponse:
    return ReminderTemplateResponse(
        id=row.id,
        organization_id=int(row.organization_id),
        created_by=int(row.created_by) if row.created_by is not None else None,
        name=row.name,
        channel=row.channel,
        subject=row.subject,
        title=row.title,
        body=row.body,
        variables=list(row.variables or []),
        is_active=bool(row.is_active),
        whatsapp_template_name=row.whatsapp_template_name,
        approval_status=row.approval_status,
        meta_template_id=row.meta_template_id,
        approved_at=row.approved_at,
        rejection_reason=row.rejection_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "",
    response_model=ReminderTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(TEMPLATES_CREATE))],
)
async def create_reminder_template(
    body: ReminderTemplateCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderTemplateResponse:
    service = ReminderTemplateService(session)
    row = await service.create_template(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        payload=body,
    )
    await session.commit()
    return _serialize(row)


@router.get(
    "",
    response_model=ReminderTemplateListResponse,
    dependencies=[Depends(PermissionChecker(TEMPLATES_VIEW))],
)
async def list_reminder_templates(
    channel: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderTemplateListResponse:
    service = ReminderTemplateService(session)
    items, total = await service.list_templates(
        organization_id=current_user.organization_id,
        channel=(channel or "").strip() or None,
        is_active=is_active,
        q=(q or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return ReminderTemplateListResponse(
        items=[_serialize(row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{template_id}",
    response_model=ReminderTemplateResponse,
    dependencies=[Depends(PermissionChecker(TEMPLATES_VIEW))],
)
async def get_reminder_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderTemplateResponse:
    service = ReminderTemplateService(session)
    try:
        row = await service.get_template(
            organization_id=current_user.organization_id,
            template_id=template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)


@router.put(
    "/{template_id}",
    response_model=ReminderTemplateResponse,
    dependencies=[Depends(PermissionChecker(TEMPLATES_UPDATE))],
)
async def update_reminder_template(
    template_id: uuid.UUID,
    body: ReminderTemplateUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReminderTemplateResponse:
    service = ReminderTemplateService(session)
    try:
        row = await service.update_template(
            organization_id=current_user.organization_id,
            template_id=template_id,
            payload=body,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    await session.commit()
    return _serialize(row)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(PermissionChecker(TEMPLATES_UPDATE))],
)
async def delete_reminder_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    service = ReminderTemplateService(session)
    try:
        await service.delete_template(
            organization_id=current_user.organization_id,
            template_id=template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
