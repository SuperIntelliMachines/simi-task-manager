from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.integrations.telegram.customer_onboarding import CustomerTelegramOnboardingService
from app.integrations.telegram.client import TelegramApiClient
from app.schemas.atm005 import WebhookEnvelope
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/telegram", tags=["telegram"])
customer_onboarding_service = CustomerTelegramOnboardingService()


@router.post("/webhook")
async def telegram_webhook(
    body: WebhookEnvelope,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="invalid telegram webhook secret")

    headers = {}
    if x_telegram_bot_api_secret_token:
        headers["x-telegram-bot-api-secret-token"] = x_telegram_bot_api_secret_token

    service = ChannelService(session)
    try:
        result = await service.process_webhook(
            channel="telegram",
            organization_id=body.organization_id,
            payload=body.payload,
            headers=headers,
            method="POST",
            raw_body=await request.body(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    bot_reply = None
    if settings.telegram_agent_bot_token:
        try:
            from app.integrations.telegram.bootstrap import ensure_models_loaded
            from app.integrations.telegram.bot_service import TelegramBotService

            ensure_models_loaded()
            bot_reply = await TelegramBotService(settings.telegram_agent_bot_token).process_webhook_update(
                body.payload,
                organization_id=body.organization_id,
            )
        except Exception as exc:
            # Keep webhook ingestion successful even if bot command handling fails.
            result = {**result, "bot_error": str(exc)}

    if bot_reply is not None:
        result = {**result, "bot_reply": bot_reply}
    return result


@router.post("/webhook/raw")
async def telegram_webhook_raw(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Direct Telegram Bot API webhook endpoint (payload only, no envelope)."""
    settings = get_settings()
    if not settings.telegram_agent_bot_token:
        raise HTTPException(status_code=503, detail="agent telegram bot is not configured")
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="invalid telegram webhook secret")

    payload = await request.json()
    from app.integrations.telegram.bootstrap import ensure_models_loaded
    from app.integrations.telegram.bot_service import TelegramBotService

    ensure_models_loaded()
    try:
        reply = await TelegramBotService(settings.telegram_agent_bot_token).process_webhook_update(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "reply": reply}


@router.post("/customer-webhook/raw")
async def telegram_customer_webhook_raw(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    """Direct customer Telegram bot webhook endpoint for policy chat onboarding."""
    settings = get_settings()
    if not settings.telegram_customer_bot_token:
        raise HTTPException(status_code=503, detail="customer telegram bot is not configured")
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="invalid telegram webhook secret")

    payload = await request.json()
    try:
        reply = await customer_onboarding_service.handle_payload(
            session=session,
            payload=payload,
        )
        if reply:
            message = payload.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is not None:
                await TelegramApiClient(settings.telegram_customer_bot_token).send_message(chat_id, reply)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "reply": reply}
