from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.telegram.bot_service import TelegramBotService
from app.integrations.telegram.handlers import WELCOME_TEXT
from app.integrations.telegram.keyboard import MenuKind


@pytest.mark.asyncio
async def test_reply_start_sends_welcome_with_main_menu():
    service = TelegramBotService()
    service.processor.register_user = AsyncMock()

    message = MagicMock()
    message.chat_id = 1001
    message.reply_text = AsyncMock(return_value=MagicMock())
    message.get_bot = MagicMock(return_value=AsyncMock())
    update = MagicMock()
    update.effective_message = message
    update.effective_user = MagicMock(id=42)

    with patch(
        "app.integrations.telegram.bot_service.dismiss_legacy_reply_keyboard",
        new=AsyncMock(),
    ) as dismiss:
        await service._reply_start(update)

    dismiss.assert_awaited_once()
    service.processor.register_user.assert_awaited_once()
    message.reply_text.assert_awaited_once()
    args, kwargs = message.reply_text.await_args
    assert args[0] == WELCOME_TEXT
    assert kwargs["reply_markup"] is not None
    assert len(kwargs["reply_markup"].inline_keyboard) == 3


@pytest.mark.asyncio
async def test_reply_rejects_empty_text():
    service = TelegramBotService()
    update = MagicMock()
    update.effective_message = MagicMock()
    update.effective_user = MagicMock(id=1)

    with pytest.raises(ValueError, match="must not be empty"):
        await service._reply(update, "   ", menu=MenuKind.MAIN)


@pytest.mark.asyncio
async def test_cmd_start_reraises_after_logging():
    service = TelegramBotService()
    service._reply_start = AsyncMock(side_effect=RuntimeError("boom"))
    update = MagicMock()

    with pytest.raises(RuntimeError, match="boom"):
        await service._cmd_start(update, MagicMock())

    service._reply_start.assert_awaited_once_with(update)


def test_welcome_text_is_non_empty():
    assert WELCOME_TEXT.strip()
    assert len(WELCOME_TEXT) > 50
    assert "🏠 Main Menu" in WELCOME_TEXT
    assert "Choose an option below  :" in WELCOME_TEXT


def test_remove_reply_keyboard_dict():
    from app.integrations.telegram.keyboard import remove_reply_keyboard_dict

    assert remove_reply_keyboard_dict() == {"remove_keyboard": True}
