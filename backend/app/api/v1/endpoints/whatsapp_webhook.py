from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.whatsapp_adapter import WhatsAppAdapter
from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.atm005 import WebhookEnvelope
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    settings = get_settings()
    adapter = WhatsAppAdapter(
        verify_token=getattr(settings, "whatsapp_verify_token", ""),
        app_secret=getattr(settings, "whatsapp_app_secret", ""),
    )
    verified, challenge = adapter.verify_webhook(
        method="GET",
        query_params={
            "hub.mode": hub_mode,
            "hub.verify_token": hub_verify_token,
            "hub.challenge": hub_challenge,
        },
        headers={},
        body=b"",
    )
    if not verified or challenge is None:
        raise HTTPException(status_code=403, detail="verification failed")
    return int(challenge) if challenge.isdigit() else challenge


@router.post("/webhook")
async def whatsapp_webhook(
    body: WebhookEnvelope,
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    adapter = WhatsAppAdapter(
        verify_token=getattr(settings, "whatsapp_verify_token", ""),
        app_secret=getattr(settings, "whatsapp_app_secret", ""),
    )

    service = ChannelService(session, whatsapp_adapter=adapter)
    headers = {}
    if x_hub_signature_256:
        headers["x-hub-signature-256"] = x_hub_signature_256

    try:
        result = await service.process_webhook(
            channel="whatsapp",
            organization_id=body.organization_id,
            payload=body.payload,
            headers=headers,
            method="POST",
            raw_body=await request.body(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result
