from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import (
    CHANNELS_CREATE,
    CHANNELS_TEST,
    CHANNELS_UPDATE,
    CHANNELS_VIEW,
)
from app.schemas.atm005 import (
    ChannelConnectionBody,
    ChannelTestMessageBody,
    ContactPreferredChannelBody,
)
from app.services.channel_service import ChannelService

router = APIRouter(
    prefix="/channel-connections",
    tags=["channel-connections"],
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
async def list_connections(
    organization_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    scoped_org_id = resolve_organization_scope(current_user, organization_id)
    service = ChannelService(session)
    rows = await service.list_connections(scoped_org_id)
    return [_serialize(row) for row in rows]


@router.post("", dependencies=[Depends(PermissionChecker(CHANNELS_CREATE))])
async def create_or_update_connection(
    body: ChannelConnectionBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    resolve_organization_scope(current_user, body.organization_id)
    service = ChannelService(session)
    row = await service.upsert_connection(**body.model_dump())
    return _serialize(row)


@router.post("/{connection_id}/test", dependencies=[Depends(PermissionChecker(CHANNELS_TEST))])
async def send_test_message(
    connection_id: int,
    body: ChannelTestMessageBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ChannelService(session)
    try:
        row = await service.test_message(
            connection_id=connection_id,
            recipient=body.recipient,
            text=body.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)


@router.put("/contacts/{contact_id}/preferred-channel", dependencies=[Depends(PermissionChecker(CHANNELS_UPDATE))])
async def set_contact_preferred_channel(
    contact_id: int,
    body: ContactPreferredChannelBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    resolve_organization_scope(current_user, body.organization_id)
    service = ChannelService(session)
    row = await service.set_contact_preferred_channel(
        organization_id=body.organization_id,
        contact_id=contact_id,
        channel=body.channel,
        external_user_id=body.external_user_id,
        external_chat_id=body.external_chat_id,
        display_name=body.display_name,
    )
    return _serialize(row)
