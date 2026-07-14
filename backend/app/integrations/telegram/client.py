"""Send outbound Telegram messages via Bot API."""

from __future__ import annotations

import logging

import httpx

from app.integrations.telegram.http_config import get_telegram_api_base, httpx_async_client_kwargs

logger = logging.getLogger(__name__)


class TelegramApiClient:
    def __init__(self, token: str | None = None):
        from app.channels.telegram_settings import resolve_telegram_bot_token

        self.token = token or resolve_telegram_bot_token()
        if not self.token:
            raise ValueError("Telegram bot token is not configured")
        self._api_base = get_telegram_api_base()

    def _api_url(self, method: str) -> str:
        return f"{self._api_base}/bot{self.token}/{method}"

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_markup: dict | None = None,
    ) -> dict:
        url = self._api_url("sendMessage")
        payload: dict = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(**httpx_async_client_kwargs()) as client:
            response = await client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception("Telegram sendMessage failed: %s", response.text)
                raise exc
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Telegram API error"))
            return data

    async def delete_message(self, chat_id: str | int, message_id: int) -> dict:
        url = self._api_url("deleteMessage")
        payload = {"chat_id": chat_id, "message_id": message_id}
        async with httpx.AsyncClient(**httpx_async_client_kwargs()) as client:
            response = await client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception("Telegram deleteMessage failed: %s", response.text)
                raise exc
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Telegram API error"))
            return data

    async def answer_callback_query(self, callback_query_id: str) -> dict:
        url = self._api_url("answerCallbackQuery")
        payload = {"callback_query_id": callback_query_id}
        async with httpx.AsyncClient(**httpx_async_client_kwargs()) as client:
            response = await client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception("Telegram answerCallbackQuery failed: %s", response.text)
                raise exc
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Telegram API error"))
            return data

    async def edit_message_text(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        *,
        reply_markup: dict | None = None,
    ) -> dict:
        url = self._api_url("editMessageText")
        payload: dict = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(**httpx_async_client_kwargs()) as client:
            response = await client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception("Telegram editMessageText failed: %s", response.text)
                raise exc
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Telegram API error"))
            return data
