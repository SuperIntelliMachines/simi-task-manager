from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import (
    TEMPLATES_APPROVE,
    TEMPLATES_CREATE,
    TEMPLATES_UPDATE,
    TEMPLATES_VIEW,
)
from app.schemas.atm017 import MessageTemplateCreateBody, MessageTemplatePatchBody, TemplateApproveBody
from app.services.message_template_service import MessageTemplateService

router = APIRouter(
    prefix="/message-templates",
    tags=["message-templates"],
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


@router.get("", dependencies=[Depends(PermissionChecker(TEMPLATES_VIEW))])
async def list_templates(
    organization_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    scoped_org_id = resolve_organization_scope(current_user, organization_id)
    service = MessageTemplateService(session)
    rows = await service.list_templates(scoped_org_id)
    return [_serialize(row) for row in rows]


@router.post("", dependencies=[Depends(PermissionChecker(TEMPLATES_CREATE))])
async def create_template(
    body: MessageTemplateCreateBody,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    resolve_organization_scope(current_user, body.organization_id)
    service = MessageTemplateService(session)
    try:
        row = await service.create_template(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize(row)


@router.patch("/{template_id}", dependencies=[Depends(PermissionChecker(TEMPLATES_UPDATE))])
async def patch_template(
    template_id: int,
    body: MessageTemplatePatchBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = MessageTemplateService(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        row = await service.update_template(template_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize(row)


@router.post("/{template_id}/approve", dependencies=[Depends(PermissionChecker(TEMPLATES_APPROVE))])
async def approve_template(
    template_id: int,
    body: TemplateApproveBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = MessageTemplateService(session)
    try:
        row = await service.approve_template(template_id, body.approver_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(row)
