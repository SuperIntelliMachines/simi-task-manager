from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db_session
from app.core.permissions import AGENTS_INVOKE, AGENTS_VIEW
from app.schemas.atm017 import AgentSessionReplyBody
from app.services.agent_session_service import AgentSessionService

router = APIRouter(
    prefix="/agent-sessions",
    tags=["agent-sessions"],
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


@router.get("/{session_id}", dependencies=[Depends(PermissionChecker(AGENTS_VIEW))])
async def get_agent_session(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    service = AgentSessionService(session)
    row = await service.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    return _serialize(row)


@router.post("/{session_id}/reply", dependencies=[Depends(PermissionChecker(AGENTS_INVOKE))])
async def reply_agent_session(
    session_id: int,
    body: AgentSessionReplyBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = AgentSessionService(session)
    try:
        row = await service.resume_session_on_reply(
            session_id=session_id,
            user_reply=body.user_reply,
            extracted_fields=body.extracted_fields,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _serialize(row)
