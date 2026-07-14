import pytest
from unittest.mock import AsyncMock, patch

from app.integrations.telegram.bootstrap import ensure_models_loaded
from app.integrations.telegram.handlers import TelegramUpdateProcessor, WELCOME_TEXT


@pytest.mark.asyncio
async def test_start_after_models_bootstrapped():
    ensure_models_loaded()
    processor = TelegramUpdateProcessor(auto_reply=False)
    payload = {
        "message": {
            "text": "/start",
            "from": {"id": 424242, "first_name": "Test"},
            "chat": {"id": 111},
        }
    }

    with patch.object(processor, "_build_reply", new=AsyncMock(return_value=WELCOME_TEXT)):
        reply = await processor.handle_payload(payload)

    assert reply == WELCOME_TEXT
    assert "Welcome to Insurance Assistant Bot" in reply


def test_models_import_registers_support_access_session():
    ensure_models_loaded()
    from app.models.support_access_sessions import SupportAccessSession
    from app.models.core import Organization

    assert Organization.support_access_sessions.property.mapper.class_ is SupportAccessSession
