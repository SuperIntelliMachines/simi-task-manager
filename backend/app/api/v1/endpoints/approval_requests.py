from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import APPROVALS_APPROVE, APPROVALS_REJECT, APPROVALS_VIEW
from app.schemas.atm017 import ApproveRejectBody
from app.services.approval_service import ApprovalService

router = APIRouter(
    prefix="/approval-requests",
    tags=["approval-requests"],
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


@router.get("", dependencies=[Depends(PermissionChecker(APPROVALS_VIEW))])
async def list_approval_requests(
    organization_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    scoped_org_id = resolve_organization_scope(current_user, organization_id)
    service = ApprovalService(session)
    rows = await service.list_requests(scoped_org_id)
    return [_serialize(row) for row in rows]


@router.post("/{request_id}/approve", dependencies=[Depends(PermissionChecker(APPROVALS_APPROVE))])
async def approve_request(
    request_id: int,
    body: ApproveRejectBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ApprovalService(session)
    try:
        row = await service.approve_request(request_id, body.actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _serialize(row)


@router.post("/{request_id}/reject", dependencies=[Depends(PermissionChecker(APPROVALS_REJECT))])
async def reject_request(
    request_id: int,
    body: ApproveRejectBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ApprovalService(session)
    try:
        row = await service.reject_request(request_id, body.actor_user_id, body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _serialize(row)
