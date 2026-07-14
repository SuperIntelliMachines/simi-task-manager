from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import CHANNELS_UPDATE, CHANNELS_VIEW
from app.schemas.atm017 import NotificationPreferenceUpdateBody
from app.services.notification_preference_service import NotificationPreferenceService

router = APIRouter(
    prefix="/notification-preferences",
    tags=["notification-preferences"],
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


@router.get("", dependencies=[Depends(PermissionChecker(CHANNELS_VIEW))])
async def list_preferences(
    organization_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    scoped_org_id = resolve_organization_scope(current_user, organization_id)
    service = NotificationPreferenceService(session)
    rows = await service.list_preferences(scoped_org_id)
    return [_serialize(row) for row in rows]


@router.put("/{preference_id}", dependencies=[Depends(PermissionChecker(CHANNELS_UPDATE))])
async def update_preference(
    preference_id: int,
    body: NotificationPreferenceUpdateBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationPreferenceService(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        row = await service.update_preference(preference_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)
