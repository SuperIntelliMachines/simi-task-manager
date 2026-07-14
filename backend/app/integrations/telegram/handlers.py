"""Process Telegram updates and route insurance commands."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from app.core.database import AsyncSessionLocal
from app.integrations.telegram.client import TelegramApiClient
from app.integrations.telegram.insurance_commands import TelegramInsuranceCommandService
from app.integrations.telegram.parsers import (
    DemoLogCommand,
    FollowupLogCommand,
    GreetingCommand,
    PolicyCreateCommand,
    PolicyQueryCommand,
    PolicyRenewCommand,
    RenewalsQueryCommand,
    normalize_intent_text,
    parse_greeting,
    parse_message,
    parse_navigation_intent,
)
from app.integrations.telegram.keyboard import (
    MAIN_MENU_PROMPT,
    MenuBack,
    MenuExecute,
    MenuKind,
    MenuOpen,
    dismiss_legacy_reply_keyboard_via_api,
    empty_inline_keyboard_dict,
    inline_keyboard_dict,
    menu_context_store,
    parse_callback_data,
)
from app.integrations.telegram.renewal_context import renewal_context_store
from app.integrations.telegram.user_context import TelegramUserContextService

logger = logging.getLogger(__name__)

MenuAttachment = MenuKind | Literal[False]

WELCOME_TEXT = (
    "🤖 Welcome to Insurance Assistant Bot.\n"
    "You can manage policies, renewals and follow-ups directly from Telegram.\n\n"
    f"{MAIN_MENU_PROMPT}"
)

GREETING_DISPLAY: dict[str, str] = {
    "hi": "Hi",
    "hello": "Hello",
    "hey": "Hey",
}


def format_greeting_text(greeting_word: str) -> str:
    """Build a greeting reply using the user's greeting type (Hi / Hello / Hey)."""
    display = GREETING_DISPLAY.get(greeting_word.strip().lower(), greeting_word.strip().capitalize())
    return (
        f"👋 {display}!\n\n"
        "Welcome to SIMI Insurance Assistant.\n\n"
        f"{MAIN_MENU_PROMPT}"
    )


def handle_greeting(greeting: GreetingCommand) -> str:
    """Handle a parsed greeting before any fallback or DB-backed command logic."""
    logger.info("Received greeting: %s", greeting.word)
    return format_greeting_text(greeting.word)


def is_greeting_reply(reply: str) -> bool:
    return reply.startswith("👋 ") and "Welcome to SIMI Insurance Assistant." in reply


MAIN_MENU_REPLY = MAIN_MENU_PROMPT


def is_main_menu_request(text: str) -> bool:
    return normalize_intent_text(text) == "main menu"


FALLBACK_HELP_TEXT = (
    "🤖 Insurance Assistant\n\n"
    "I didn't understand that request.\n\n"
    "Try:\n"
    "• Show dashboard\n"
    "• Show policies\n"
    "• Show active policies\n"
    "• Show expiring policies\n"
    "• Show pending follow-ups\n\n"
    "Or send /help."
)


def fallback_help_message() -> str:
    return FALLBACK_HELP_TEXT


@dataclass(frozen=True)
class HandlerReply:
    text: str
    menu: MenuAttachment = MenuKind.MAIN


def should_attach_main_menu(*, command_text: str, reply: str) -> bool:
    """Whether a text reply should include the main inline menu."""
    if is_main_menu_request(command_text):
        return True
    parsed = parse_message(command_text)
    if parsed == "/start":
        return True
    if isinstance(parsed, GreetingCommand):
        return True
    if reply in {WELCOME_TEXT, MAIN_MENU_REPLY}:
        return True
    if is_greeting_reply(reply):
        return True
    return False


def _reply_markup_for_menu(menu: MenuAttachment, *, editing: bool = False) -> dict | None:
    if menu is False:
        return empty_inline_keyboard_dict() if editing else None
    return inline_keyboard_dict(menu)


class TelegramUpdateProcessor:
    """Shared update processor for webhook and polling modes."""

    def __init__(self, *, auto_reply: bool = True, token: str | None = None):
        self.auto_reply = auto_reply
        self.token = token

    async def _send_telegram_reply(
        self,
        *,
        chat_id: str | int,
        text: str,
        external_user_id: str,
        menu: MenuAttachment = False,
        dismiss_reply_keyboard: bool = False,
    ) -> None:
        if not self.auto_reply or not self.token:
            return
        client = TelegramApiClient(self.token)
        if dismiss_reply_keyboard:
            await dismiss_legacy_reply_keyboard_via_api(client, chat_id)
        await client.send_message(
            chat_id,
            text,
            reply_markup=_reply_markup_for_menu(menu),
        )

    async def _edit_telegram_message(
        self,
        *,
        chat_id: str | int,
        message_id: int,
        text: str,
        menu: MenuAttachment,
    ) -> None:
        if not self.auto_reply or not self.token:
            return
        client = TelegramApiClient(self.token)
        markup = _reply_markup_for_menu(menu, editing=True)
        try:
            await client.edit_message_text(
                chat_id,
                message_id,
                text,
                reply_markup=markup,
            )
        except Exception as exc:
            logger.warning("Telegram editMessageText failed, falling back to sendMessage: %s", exc)
            await client.send_message(chat_id, text, reply_markup=markup)

    async def _handle_menu_interaction(
        self,
        interaction: MenuOpen | MenuBack | MenuExecute,
        *,
        external_user_id: str,
        external_chat_id: str,
        display_name: str | None,
        organization_id: int | None,
    ) -> str:
        if isinstance(interaction, MenuOpen):
            menu_context_store.set(external_user_id, interaction.menu)
            return interaction.prompt

        if isinstance(interaction, MenuBack):
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            return interaction.prompt

        menu_context_store.set(external_user_id, interaction.menu)
        async with AsyncSessionLocal() as session:
            ctx = await TelegramUserContextService(session).resolve(
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
                display_name=display_name,
                organization_id=organization_id,
            )
            service = TelegramInsuranceCommandService(
                session,
                organization_id=ctx.organization_id,
                actor_user_id=ctx.actor_user_id,
            )
            return await service.execute_menu_action(interaction.action)

    async def register_user(
        self,
        payload: dict[str, Any],
        *,
        organization_id: int | None = None,
    ) -> None:
        """Best-effort Telegram user → organization link (never raises)."""
        message = payload.get("message") or {}
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}
        external_user_id = str(from_user.get("id", ""))
        chat_id = chat.get("id")
        if not external_user_id or chat_id is None:
            return

        display_name = " ".join(
            part for part in [from_user.get("first_name"), from_user.get("last_name")] if part
        ) or from_user.get("username")

        try:
            async with AsyncSessionLocal() as session:
                await TelegramUserContextService(session).resolve(
                    external_user_id=external_user_id,
                    external_chat_id=str(chat_id),
                    display_name=display_name,
                    organization_id=organization_id,
                )
        except Exception as exc:
            logger.exception(
                "Telegram user registration failed user=%s chat=%s error_type=%s error=%s",
                external_user_id,
                chat_id,
                type(exc).__name__,
                exc,
            )

    async def handle_payload(self, payload: dict[str, Any], *, organization_id: int | None = None) -> str | None:
        if payload.get("callback_query"):
            result = await self.handle_callback_payload(payload, organization_id=organization_id)
            return result.text if result else None

        message = payload.get("message") or {}
        text = message.get("text")
        if not text:
            return None

        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        chat_id = chat.get("id")
        external_user_id = str(from_user.get("id", ""))
        if not external_user_id or chat_id is None:
            return None

        display_name = " ".join(
            part for part in [from_user.get("first_name"), from_user.get("last_name")] if part
        ) or from_user.get("username")

        logger.info(
            "Telegram incoming message user=%s chat=%s text=%r",
            external_user_id,
            chat_id,
            text,
        )

        if normalize_intent_text(text).startswith("/"):
            renewal_context_store.clear(external_user_id)
            if normalize_intent_text(text).split()[0] in {"/start", "/help"}:
                menu_context_store.set(external_user_id, MenuKind.MAIN)

        if renewal_context_store.get(external_user_id) is not None:
            parsed_command = parse_message(text)
            if parsed_command is not None:
                renewal_context_store.clear(external_user_id)
            else:
                pending_reply = await self._handle_pending_renewal_date(
                    text=text,
                    external_user_id=external_user_id,
                    external_chat_id=str(chat_id),
                    display_name=display_name,
                    organization_id=organization_id,
                )
                if pending_reply:
                    await self._send_telegram_reply(
                        chat_id=chat_id,
                        text=pending_reply,
                        external_user_id=external_user_id,
                    )
                    return pending_reply

        greeting = parse_greeting(text)
        if greeting is not None:
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            reply = handle_greeting(greeting)
            if reply:
                await self._send_telegram_reply(
                    chat_id=chat_id,
                    text=reply,
                    external_user_id=external_user_id,
                    menu=MenuKind.MAIN,
                )
            return reply

        if is_main_menu_request(text):
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            reply = MAIN_MENU_REPLY
            await self._send_telegram_reply(
                chat_id=chat_id,
                text=reply,
                external_user_id=external_user_id,
                menu=MenuKind.MAIN,
            )
            return reply

        navigation_command = parse_navigation_intent(text)
        if navigation_command is not None:
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            try:
                reply = await self._build_reply(
                    text=navigation_command,
                    external_user_id=external_user_id,
                    external_chat_id=str(chat_id),
                    display_name=display_name,
                    organization_id=organization_id,
                )
            except Exception as exc:
                logger.exception(
                    "Telegram navigation command failed user=%s chat=%s command=%s text=%r error_type=%s error=%s",
                    external_user_id,
                    chat_id,
                    navigation_command,
                    text,
                    type(exc).__name__,
                    exc,
                )
                reply = (
                    "⚠️ Something went wrong while processing your request.\n"
                    "Please try again later or send /help for available commands."
                )

            if reply:
                await self._send_telegram_reply(
                    chat_id=chat_id,
                    text=reply,
                    external_user_id=external_user_id,
                )
            return reply

        try:
            reply = await self._build_reply(
                text=text,
                external_user_id=external_user_id,
                external_chat_id=str(chat_id),
                display_name=display_name,
                organization_id=organization_id,
            )
        except Exception as exc:
            logger.exception(
                "Telegram command failed user=%s chat=%s text=%r error_type=%s error=%s",
                external_user_id,
                chat_id,
                text,
                type(exc).__name__,
                exc,
            )
            reply = (
                "⚠️ Something went wrong while processing your request.\n"
                "Please try again later or send /help for available commands."
            )

        if reply == FALLBACK_HELP_TEXT:
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            self._log_unknown_message(external_user_id, chat_id, text)
        elif isinstance(parse_message(text), str) and parse_message(text) == "/start":
            menu_context_store.set(external_user_id, MenuKind.MAIN)

        if reply:
            attach_menu: MenuAttachment = (
                MenuKind.MAIN if should_attach_main_menu(command_text=text, reply=reply) else False
            )
            await self._send_telegram_reply(
                chat_id=chat_id,
                text=reply,
                external_user_id=external_user_id,
                menu=attach_menu,
                dismiss_reply_keyboard=reply == WELCOME_TEXT,
            )
        return reply

    async def handle_callback_payload(
        self,
        payload: dict[str, Any],
        *,
        organization_id: int | None = None,
    ) -> HandlerReply | None:
        callback = payload.get("callback_query") or {}
        data = callback.get("data")
        interaction = parse_callback_data(data)
        if interaction is None:
            logger.info("Telegram unknown callback data=%r", data)
            return HandlerReply(fallback_help_message(), False)

        from_user = callback.get("from") or {}
        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        external_user_id = str(from_user.get("id", ""))
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        if not external_user_id or chat_id is None:
            return None

        display_name = " ".join(
            part for part in [from_user.get("first_name"), from_user.get("last_name")] if part
        ) or from_user.get("username")

        logger.info(
            "Telegram callback user=%s chat=%s data=%r interaction=%r",
            external_user_id,
            chat_id,
            data,
            interaction,
        )

        try:
            handler_reply = await self._resolve_menu_interaction(
                interaction,
                external_user_id=external_user_id,
                external_chat_id=str(chat_id),
                display_name=display_name,
                organization_id=organization_id,
            )
        except Exception as exc:
            logger.exception(
                "Telegram callback failed user=%s data=%r error_type=%s error=%s",
                external_user_id,
                data,
                type(exc).__name__,
                exc,
            )
            handler_reply = HandlerReply(
                "⚠️ Something went wrong while processing your request.\n"
                "Please try again later or send /help for available commands.",
                False,
            )

        if handler_reply and self.auto_reply:
            client = TelegramApiClient(self.token)
            callback_id = callback.get("id")
            if callback_id:
                await client.answer_callback_query(callback_id)
            if message_id is not None:
                await self._edit_telegram_message(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=handler_reply.text,
                    menu=handler_reply.menu,
                )
            else:
                await self._send_telegram_reply(
                    chat_id=chat_id,
                    text=handler_reply.text,
                    external_user_id=external_user_id,
                    menu=handler_reply.menu,
                )

        return handler_reply

    async def _resolve_menu_interaction(
        self,
        interaction: MenuOpen | MenuBack | MenuExecute,
        *,
        external_user_id: str,
        external_chat_id: str,
        display_name: str | None,
        organization_id: int | None,
    ) -> HandlerReply:
        if isinstance(interaction, MenuOpen):
            menu_context_store.set(external_user_id, interaction.menu)
            return HandlerReply(interaction.prompt, interaction.menu)

        if isinstance(interaction, MenuBack):
            menu_context_store.set(external_user_id, MenuKind.MAIN)
            return HandlerReply(interaction.prompt, MenuKind.MAIN)

        menu_context_store.set(external_user_id, interaction.menu)
        text = await self._handle_menu_interaction(
            interaction,
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            display_name=display_name,
            organization_id=organization_id,
        )
        return HandlerReply(text, interaction.menu)

    @staticmethod
    def _log_unknown_message(external_user_id: str, chat_id: str | int, text: str) -> None:
        logger.info(
            "Telegram unknown input user=%s chat=%s text=%r",
            external_user_id,
            chat_id,
            text,
        )

    async def _build_reply(
        self,
        *,
        text: str,
        external_user_id: str,
        external_chat_id: str,
        display_name: str | None,
        organization_id: int | None,
    ) -> str | None:
        async with AsyncSessionLocal() as session:
            ctx = await TelegramUserContextService(session).resolve(
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
                display_name=display_name,
                organization_id=organization_id,
            )
            service = TelegramInsuranceCommandService(
                session,
                organization_id=ctx.organization_id,
                actor_user_id=ctx.actor_user_id,
            )
            return await self._dispatch(service, text, external_user_id=external_user_id)

    async def _handle_pending_renewal_date(
        self,
        *,
        text: str,
        external_user_id: str,
        external_chat_id: str,
        display_name: str | None,
        organization_id: int | None,
    ) -> str | None:
        async with AsyncSessionLocal() as session:
            ctx = await TelegramUserContextService(session).resolve(
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
                display_name=display_name,
                organization_id=organization_id,
            )
            service = TelegramInsuranceCommandService(
                session,
                organization_id=ctx.organization_id,
                actor_user_id=ctx.actor_user_id,
            )
            return await service.complete_policy_renewal(
                external_user_id=external_user_id,
                date_text=text,
            )

    async def _dispatch(
        self,
        service: TelegramInsuranceCommandService,
        text: str,
        *,
        external_user_id: str,
    ) -> str | None:
        parsed = parse_message(text)
        logger.info("Telegram parsed message text=%r parsed=%r", text, parsed)

        if isinstance(parsed, GreetingCommand):
            return handle_greeting(parsed)

        if parsed is None:
            logger.info(
                "Telegram no intent matched text=%r normalized=%r",
                text,
                normalize_intent_text(text),
            )
            return fallback_help_message()

        if isinstance(parsed, str):
            if parsed == "/start":
                return WELCOME_TEXT
            if parsed == "/help":
                return await service.help_message()
            if parsed == "/dashboard":
                return await service.dashboard_summary()
            if parsed == "/policies":
                return await service.policies_summary()
            if parsed == "/followups":
                return await service.followups_summary()
            if parsed == "/renewals":
                return await service.renewals_summary()
            return fallback_help_message()

        if parsed == "followups":
            return await service.followups_summary()

        if isinstance(parsed, DemoLogCommand):
            return await service.log_demo(
                customer_name=parsed.customer_name,
                followup_days=parsed.followup_days,
            )

        if isinstance(parsed, FollowupLogCommand):
            return await service.log_followup(
                customer_name=parsed.customer_name,
                followup_days=parsed.followup_days,
                notes=parsed.notes,
            )

        if isinstance(parsed, PolicyCreateCommand):
            return await service.create_policy(
                customer_name=parsed.customer_name,
                policy_type=parsed.policy_type,
                expiry_date=parsed.expiry_date,
                reminder_channel=parsed.reminder_channel,
            )

        if isinstance(parsed, PolicyRenewCommand):
            return await service.start_policy_renewal(
                customer_name=parsed.customer_name,
                external_user_id=external_user_id,
            )

        if isinstance(parsed, RenewalsQueryCommand):
            logger.info(
                "Telegram dispatch expiring policies query days=%s user=%s",
                parsed.days,
                external_user_id,
            )
            return await service.expiring_policies_within_days(days=parsed.days)

        if isinstance(parsed, PolicyQueryCommand):
            return await service.execute_menu_action(parsed.action)

        return fallback_help_message()
