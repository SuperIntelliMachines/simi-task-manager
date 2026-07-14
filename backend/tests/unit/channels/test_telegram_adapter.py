from datetime import UTC, datetime

import pytest

from app.channels.telegram_adapter import TelegramAdapter


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_telegram_webhook_normalizes_text_message():
    adapter = TelegramAdapter()
    payload = {
        "update_id": 1001,
        "message": {
            "message_id": 10,
            "text": "hello",
            "from": {"id": 1234},
            "chat": {"id": 5678},
        },
    }

    normalized = adapter.normalize_inbound_payload(payload)
    assert normalized.text == "hello"
    assert normalized.external_user_id == "1234"
    assert normalized.external_chat_id == "5678"


@pytest.mark.asyncio
async def test_telegram_inline_button_parses_action():
    adapter = TelegramAdapter()
    payload = {
        "update_id": 1002,
        "callback_query": {
            "id": "cb1",
            "data": "complete:task:77",
            "from": {"id": 1234},
            "message": {"chat": {"id": 5678}},
        },
    }

    normalized = adapter.normalize_inbound_payload(payload)
    assert normalized.action == "complete"
    assert normalized.action_payload == {"task_id": 77}
