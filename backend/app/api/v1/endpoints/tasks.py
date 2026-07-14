from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import (
    TASKS_COMPLETE,
    TASKS_CREATE,
    TASKS_UPDATE,
    TASKS_VIEW,
)
from app.schemas.atm004 import TaskCompleteBody, TaskCreateBody, TaskPatchBody, TaskSnoozeBody
from app.services.task_service import TaskService

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(item):
    data = {}
    for key, value in item.__dict__.items():
        if key.startswith("_"):
            continue
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data


def _map_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if "cross-tenant" in detail:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post("", dependencies=[Depends(PermissionChecker(TASKS_CREATE))])
async def create_task(
    body: TaskCreateBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    organization_id = resolve_organization_scope(current_user, body.organization_id)
    service = TaskService(session)
    payload = body.model_dump()
    payload["organization_id"] = organization_id
    item = await service.create_task(**payload)
    return _serialize(item)


@router.get("", dependencies=[Depends(PermissionChecker(TASKS_VIEW))])
async def list_tasks(
    organization_id: int = Query(...),
    status: str | None = Query(None),
    domain: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    scoped_org_id = resolve_organization_scope(current_user, organization_id)
    service = TaskService(session)
    rows = await service.list_tasks(organization_id=scoped_org_id, status=status, domain=domain)
    return [_serialize(row) for row in rows]


@router.patch("/{task_id}", dependencies=[Depends(PermissionChecker(TASKS_UPDATE))])
async def patch_task(
    task_id: int,
    body: TaskPatchBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    organization_id = int(current_user.organization_id)
    service = TaskService(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None and k != "actor_user_id"}
    try:
        item = await service.update_task(
            task_id,
            updates,
            actor_user_id=body.actor_user_id,
            organization_id=organization_id,
        )
    except ValueError as exc:
        raise _map_service_error(exc) from exc
    return _serialize(item)


@router.post("/{task_id}/complete", dependencies=[Depends(PermissionChecker(TASKS_COMPLETE))])
async def complete_task(
    task_id: int,
    body: TaskCompleteBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    organization_id = int(current_user.organization_id)
    service = TaskService(session)
    try:
        item = await service.complete_task(
            task_id,
            actor_user_id=body.actor_user_id,
            cancel_future_reminders=body.cancel_future_reminders,
            organization_id=organization_id,
        )
    except ValueError as exc:
        raise _map_service_error(exc) from exc
    return _serialize(item)


@router.post("/{task_id}/snooze", dependencies=[Depends(PermissionChecker(TASKS_UPDATE))])
async def snooze_task(
    task_id: int,
    body: TaskSnoozeBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    organization_id = int(current_user.organization_id)
    service = TaskService(session)
    try:
        item = await service.snooze_task(
            task_id,
            due_at=body.due_at,
            actor_user_id=body.actor_user_id,
            organization_id=organization_id,
        )
    except ValueError as exc:
        raise _map_service_error(exc) from exc
    return _serialize(item)
