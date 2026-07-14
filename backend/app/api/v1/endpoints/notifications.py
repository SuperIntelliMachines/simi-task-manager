"""Generic in-app notification APIs (module-agnostic)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.database import get_db_session
from app.models.notification import Notification
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(row: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=row.id,
        organization_id=int(row.organization_id),
        user_id=int(row.user_id),
        entity_type=row.entity_type,
        entity_id=int(row.entity_id),
        reminder_instance_id=int(row.reminder_instance_id) if row.reminder_instance_id is not None else None,
        title=row.title,
        message=row.message,
        priority=row.priority,
        status=row.status,
        metadata=dict(row.metadata_json or {}),
        created_at=row.created_at,
        read_at=row.read_at,
        created_by=int(row.created_by) if row.created_by is not None else None,
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> NotificationListResponse:
    service = NotificationService(session)
    rows = await service.list_notifications(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        status=(status or "").strip().upper() or None,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(notifications=[_serialize(row) for row in rows])


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UnreadCountResponse:
    service = NotificationService(session)
    count = await service.unread_count(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> NotificationResponse:
    service = NotificationService(session)
    try:
        row = await service.mark_as_read(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            notification_id=notification_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _serialize(row)


@router.patch("/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> MarkAllReadResponse:
    service = NotificationService(session)
    updated = await service.mark_all_as_read(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    await session.commit()
    return MarkAllReadResponse(updated=updated)


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, bool]:
    service = NotificationService(session)
    try:
        await service.delete_notification(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            notification_id=notification_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return {"deleted": True}
