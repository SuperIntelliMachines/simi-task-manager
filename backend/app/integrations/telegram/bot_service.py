"""Telegram bot application setup (polling + webhook helpers)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from telegram import Update
from telegram.error import Conflict
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.config import get_settings
from app.integrations.telegram.bootstrap import ensure_models_loaded, prepare_telegram_runtime
from app.integrations.telegram.handlers import (
    TelegramUpdateProcessor,
    WELCOME_TEXT,
    fallback_help_message,
    should_attach_main_menu,
)
from app.integrations.telegram.http_config import build_ptb_http_request
from app.integrations.telegram.keyboard import (
    MenuKind,
    dismiss_legacy_reply_keyboard,
    inline_keyboard,
    menu_context_store,
    parse_callback_data,
)

MenuAttachment = MenuKind | Literal[False]

logger = logging.getLogger(__name__)

KNOWN_COMMANDS = filters.Regex(r"^/(?:start|help|dashboard|policies|followups|renewals)(?:@\w+)?(?:\s|$)")


class TelegramBotService:
    def __init__(self, token: str | None = None):
        ensure_models_loaded()
        settings = get_settings()
        self.token = token or settings.telegram_agent_bot_token
        if not self.token:
            raise ValueError("TELEGRAM_AGENT_BOT_TOKEN is not configured")
        self.processor = TelegramUpdateProcessor(auto_reply=False, token=self.token)

    def build_application(self) -> Application:
        application = (
            Application.builder()
            .token(self.token)
            .request(build_ptb_http_request())
            .post_init(self._on_post_init)
            .post_shutdown(self._on_post_shutdown)
            .build()
        )
        application.add_handler(CommandHandler("start", self._cmd_start))
        application.add_handler(CommandHandler("help", self._cmd_help))
        application.add_handler(CommandHandler("dashboard", self._cmd_dashboard))
        application.add_handler(CommandHandler("policies", self._cmd_policies))
        application.add_handler(CommandHandler("followups", self._cmd_followups))
        application.add_handler(CommandHandler("renewals", self._cmd_renewals))
        application.add_handler(CallbackQueryHandler(self._on_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))
        application.add_handler(
            MessageHandler(filters.COMMAND & ~KNOWN_COMMANDS, self._on_unknown_command)
        )
        application.add_error_handler(self._on_error)
        return application

    async def process_webhook_update(
        self,
        payload: dict[str, Any],
        *,
        organization_id: int | None = None,
    ) -> str | None:
        processor = TelegramUpdateProcessor(auto_reply=True, token=self.token)
        return await processor.handle_payload(payload, organization_id=organization_id)

    def run_polling(self) -> None:
        logger.info("Starting Telegram bot polling...")
        application = self.build_application()
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

    async def _on_post_init(self, application: Application) -> None:
        await prepare_telegram_runtime()

    async def _on_post_shutdown(self, application: Application) -> None:
        from app.integrations.telegram.bootstrap import reset_async_engine_pool

        await reset_async_engine_pool()

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await self._reply_start(update)
        except Exception:
            logger.exception("Start handler failed")
            raise

    async def _reply(
        self,
        update: Update,
        text: str,
        *,
        menu: MenuAttachment = MenuKind.MAIN,
    ) -> None:
        if update.effective_message is None:
            logger.warning("Telegram _reply skipped: no effective_message")
            return

        message_text = str(text or "")
        if not message_text.strip():
            menu_label = menu.value if isinstance(menu, MenuKind) else "none"
            logger.exception("Telegram _reply called with empty text menu=%s", menu_label)
            raise ValueError("Telegram reply text must not be empty")

        user = update.effective_user
        if user is not None and isinstance(menu, MenuKind):
            menu_context_store.set(str(user.id), menu)

        markup = inline_keyboard(menu) if menu is not False else None
        menu_label = menu.value if isinstance(menu, MenuKind) else "none"
        logger.info(
            "Telegram sending reply user=%s text_len=%s menu=%s",
            user.id if user else "?",
            len(message_text),
            menu_label,
        )
        await update.effective_message.reply_text(message_text, reply_markup=markup)

    async def _reply_start(self, update: Update) -> None:
        try:
            await self.processor.register_user(update.to_dict())
            user = update.effective_user
            if user is not None:
                menu_context_store.set(str(user.id), MenuKind.MAIN)
            logger.info(
                "Start command welcome text_len=%s user=%s",
                len(WELCOME_TEXT),
                user.id if user else "?",
            )
            message = update.effective_message
            if message is not None:
                await dismiss_legacy_reply_keyboard(message.get_bot(), message.chat_id)
            await self._reply(update, WELCOME_TEXT, menu=MenuKind.MAIN)
        except Exception:
            logger.exception("Start command failed")
            raise

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._dispatch_update(update, "/help")

    async def _cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._dispatch_update(update, "/dashboard")

    async def _cmd_policies(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._dispatch_update(update, "/policies")

    async def _cmd_followups(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._dispatch_update(update, "/followups")

    async def _cmd_renewals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._dispatch_update(update, "/renewals")

    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()

        if query.data and parse_callback_data(query.data) is None:
            if query.message is not None:
                user = update.effective_user
                if user is not None:
                    menu_context_store.set(str(user.id), MenuKind.MAIN)
                await query.message.edit_text(
                    fallback_help_message(),
                    reply_markup=inline_keyboard([]),
                )
            return

        payload = update.to_dict()
        try:
            handler_reply = await self.processor.handle_callback_payload(payload)
        except Exception:
            logger.exception("Telegram callback handler failed data=%r", query.data)
            raise

        if not handler_reply or query.message is None:
            return

        user = update.effective_user
        if user is not None and handler_reply.menu is not False:
            menu_context_store.set(str(user.id), handler_reply.menu)

        markup = (
            inline_keyboard([])
            if handler_reply.menu is False
            else inline_keyboard(handler_reply.menu)
        )
        try:
            await query.message.edit_text(
                handler_reply.text,
                reply_markup=markup,
            )
        except Exception as exc:
            logger.exception("Telegram edit_message failed, sending new message: %s", exc)
            await query.message.reply_text(
                handler_reply.text,
                reply_markup=markup,
            )

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None or not message.text:
            return
        logger.info("Telegram raw incoming message text=%r", message.text)
        await self._dispatch_update(update, message.text)

    async def _on_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None or not message.text:
            return
        user = update.effective_user
        chat = update.effective_chat
        TelegramUpdateProcessor._log_unknown_message(
            str(user.id if user else ""),
            chat.id if chat else "",
            message.text,
        )
        await self._reply(update, fallback_help_message(), menu=False)

    async def _dispatch_update(self, update: Update, text: str) -> None:
        payload = update.to_dict()
        if "message" in payload and payload["message"] is not None:
            payload["message"]["text"] = text

        try:
            reply = await self.processor.handle_payload(payload)
        except Exception:
            logger.exception("Telegram dispatch failed text=%r", text)
            raise

        if reply and update.effective_message is not None:
            attach = should_attach_main_menu(command_text=text, reply=reply)
            markup = inline_keyboard(MenuKind.MAIN) if attach else None
            await update.effective_message.reply_text(reply, reply_markup=markup)

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        if isinstance(error, Conflict):
            logger.warning(
                "Telegram polling conflict — another bot instance may be running: %s",
                error,
            )
            return

        logger.exception(
            "Telegram handler error update=%r error_type=%s error=%s",
            update,
            type(error).__name__ if error else "Unknown",
            error,
        )
