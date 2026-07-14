import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.channels.base import ChannelAdapter, NormalizedInboundMessage
from app.channels.whatsapp_template_layout import (
    build_template_components,
    resolve_template_language,
    resolve_template_layout,
)
from app.core.config import get_settings
from app.utils.policy_mobile import normalize_whatsapp_recipient

logger = logging.getLogger(__name__)


class WhatsAppAdapter(ChannelAdapter):
    channel_name = "whatsapp"

    def __init__(self, verify_token: str | None = None, app_secret: str | None = None):
        self.verify_token = verify_token or ""
        self.app_secret = app_secret or ""

    def normalize_inbound_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedInboundMessage:
        entry = (payload.get("entry") or [{}])[0]
        change = (entry.get("changes") or [{}])[0]
        value = change.get("value", {})
        messages = value.get("messages") or [{}]
        message = messages[0]
        contacts = value.get("contacts") or [{}]
        contact = contacts[0]
        text_body = ((message.get("text") or {}).get("body") or "").strip()

        return NormalizedInboundMessage(
            channel=self.channel_name,
            external_message_id=str(message.get("id", "")),
            external_user_id=str(message.get("from", contact.get("wa_id", ""))),
            external_chat_id=str(message.get("from", contact.get("wa_id", ""))),
            text=text_body,
            message_type=message.get("type", "text"),
            raw_payload=payload,
        )

    async def _post_message_payload(
        self,
        *,
        url: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> str:
        logger.info("[WhatsAppAdapter] sending request url=%s payload=%s", url, payload)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response_body = response.text
        logger.info(
            "[WhatsAppAdapter] response status=%s body=%s",
            response.status_code,
            response_body,
        )

        if response.status_code not in {200, 201}:
            logger.error(
                "[WhatsAppAdapter] send failed status=%s body=%s",
                response.status_code,
                response_body,
            )
            raise RuntimeError(
                f"whatsapp api send failed status={response.status_code} body={response_body}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.error(
                "[WhatsAppAdapter] invalid json response status=%s body=%s",
                response.status_code,
                response_body,
            )
            raise RuntimeError(
                f"whatsapp api send returned invalid json status={response.status_code}"
            ) from exc

        contacts = data.get("contacts")
        if isinstance(contacts, list) and contacts:
            for index, contact in enumerate(contacts):
                if not isinstance(contact, dict):
                    continue
                logger.info(
                    "[WhatsAppAdapter] response contact[%s] input=%s wa_id=%s",
                    index,
                    contact.get("input"),
                    contact.get("wa_id"),
                )
                wa_id = str(contact.get("wa_id", "")).strip()
                if not wa_id:
                    logger.warning(
                        "[WhatsAppAdapter] response contact[%s] missing wa_id — "
                        "number may not be registered on WhatsApp",
                        index,
                    )
        else:
            logger.warning(
                "[WhatsAppAdapter] response missing contacts[] status=%s body=%s",
                response.status_code,
                response_body,
            )

        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            logger.error(
                "[WhatsAppAdapter] missing message id status=%s body=%s",
                response.status_code,
                response_body,
            )
            raise RuntimeError(
                f"whatsapp api send missing message id status={response.status_code} body={response_body}"
            )
        message_id = str((messages[0] or {}).get("id", "")).strip()
        if not message_id:
            logger.error(
                "[WhatsAppAdapter] empty message id status=%s body=%s",
                response.status_code,
                response_body,
            )
            raise RuntimeError(
                f"whatsapp api send missing message id status={response.status_code} body={response_body}"
            )
        logger.info(
            "[WhatsAppAdapter] send accepted message_id=%s http_status=%s",
            message_id,
            response.status_code,
        )
        return message_id

    async def send_outbound_message(
        self,
        *,
        connection_settings: dict[str, Any],
        recipient: str,
        text: str,
        template_name: str | None = None,
        template_language: str | None = None,
        template_variables: dict[str, str] | None = None,
    ) -> str:
        settings = get_settings()

        access_token = (
            str(connection_settings.get("accessToken", "")).strip()
            or settings.whatsapp_access_token.strip()
        )
        phone_number_id = (
            str(connection_settings.get("phoneNumberId", "")).strip()
            or settings.whatsapp_phone_number_id.strip()
        )
        api_version = (
            str(connection_settings.get("apiVersion", "")).strip()
            or settings.whatsapp_api_version.strip()
            or "v22.0"
        )

        if not access_token:
            raise ValueError("missing WHATSAPP_ACCESS_TOKEN")
        if not phone_number_id:
            raise ValueError("missing WHATSAPP_PHONE_NUMBER_ID")

        recipient = normalize_whatsapp_recipient(recipient)
        if not recipient:
            raise ValueError("missing whatsapp recipient phone number")

        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

        session_text_override = connection_settings.get("use_whatsapp_session_text")
        if session_text_override is None:
            session_text_override = connection_settings.get("useWhatsAppSessionText")

        use_session_text = settings.use_whatsapp_session_text
        if session_text_override is not None:
            if isinstance(session_text_override, str):
                use_session_text = session_text_override.strip().lower() in {"1", "true", "yes", "on"}
            else:
                use_session_text = bool(session_text_override)

        if use_session_text:
            body = (text or "").strip()
            if not body:
                raise ValueError("missing whatsapp session text body")
            payload: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": body},
            }
            logger.info("[WhatsAppAdapter] session text mode enabled body_length=%s to=%s", len(body), recipient)
            return await self._post_message_payload(
                url=url,
                access_token=access_token,
                payload=payload,
            )

        resolved_template_name = (
            template_name
            or str(connection_settings.get("templateName", "")).strip()
            or settings.whatsapp_template_name.strip()
            or "welcome"
        )
        logger.info("Using WhatsApp template: %s", resolved_template_name)
        language_code = resolve_template_language(
            resolved_template_name,
            connection_settings,
            template_language=template_language,
            env_language=settings.whatsapp_template_language.strip(),
        )

        layout = resolve_template_layout(resolved_template_name, connection_settings)

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": resolved_template_name,
                "language": {"code": language_code},
            },
        }

        components = build_template_components(layout, template_variables)
        if components:
            payload["template"]["components"] = components

        body_params: list[str] = []
        for component in components:
            if component.get("type") == "body":
                for param in component.get("parameters") or []:
                    if isinstance(param, dict) and param.get("type") == "text":
                        body_params.append(str(param.get("text", "")))

        logger.info(
            "[WhatsAppAdapter] resolved template=%s language=%s layout=%s",
            resolved_template_name,
            language_code,
            layout,
        )
        logger.info(
            "[WhatsAppAdapter] template send to=%s template=%s language=%s "
            "body_param_count=%s body_params=%s phone_number_id=%s",
            recipient,
            resolved_template_name,
            language_code,
            len(body_params),
            body_params,
            phone_number_id,
        )
        logger.info(
            "[WhatsAppAdapter] template mode components=%s",
            len(components),
        )
        message_id = await self._post_message_payload(
            url=url,
            access_token=access_token,
            payload=payload,
        )
        logger.info(
            "[WhatsAppAdapter] template send accepted template_name=%s template_language=%s "
            "provider_message_id=%s",
            resolved_template_name,
            language_code,
            message_id,
        )
        return message_id

    def verify_webhook(
        self,
        *,
        method: str,
        query_params: dict[str, str],
        headers: dict[str, str],
        body: bytes,
    ) -> tuple[bool, str | None]:
        if method.upper() == "GET":
            mode = query_params.get("hub.mode")
            token = query_params.get("hub.verify_token")
            challenge = query_params.get("hub.challenge")
            if mode == "subscribe" and token == self.verify_token:
                return True, challenge
            return False, None

        signature = headers.get("x-hub-signature-256", "")
        if self.app_secret and signature:
            digest = hmac.new(self.app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            expected = f"sha256={digest}"
            if not hmac.compare_digest(expected, signature):
                return False, None

        return True, None

    def resolve_identity(self, normalized: NormalizedInboundMessage) -> dict[str, str | None]:
        return {
            "external_user_id": normalized.external_user_id,
            "external_chat_id": normalized.external_chat_id,
        }

    def map_provider_error(self, error: Exception) -> dict[str, str]:
        return {"code": "whatsapp_error", "message": str(error)}
