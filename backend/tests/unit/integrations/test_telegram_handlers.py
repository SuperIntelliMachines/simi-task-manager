from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.telegram.handlers import (
    HandlerReply,
    MAIN_MENU_REPLY,
    TelegramUpdateProcessor,
    WELCOME_TEXT,
    fallback_help_message,
    should_attach_main_menu,
)
from app.integrations.telegram.insurance_commands import TelegramInsuranceCommandService
from app.integrations.telegram.keyboard import CB_ACTION_KPI, CB_MAIN_DASHBOARD, CB_MAIN_HELP, MenuKind, menu_context_store
from app.integrations.telegram.renewal_context import renewal_context_store
from app.models.verticals import InsurancePolicy
from app.utils.datetime_utils import utcnow_naive


@pytest.fixture(autouse=True)
def clear_renewal_store():
    renewal_context_store._pending.clear()
    menu_context_store._menus.clear()
    yield
    renewal_context_store._pending.clear()
    menu_context_store._menus.clear()


@pytest.mark.asyncio
async def test_processor_dispatches_slash_commands():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.help_message = AsyncMock(return_value="help text")
    service.dashboard_summary = AsyncMock(return_value="dashboard text")
    service.policies_summary = AsyncMock(return_value="policies text")
    service.followups_summary = AsyncMock(return_value="followups text")
    service.renewals_summary = AsyncMock(return_value="renewals text")

    start_reply = await processor._dispatch(service, "/start", external_user_id="u1")
    assert "Welcome to Insurance Assistant Bot" in start_reply

    assert await processor._dispatch(service, "/help", external_user_id="u1") == "help text"
    assert await processor._dispatch(service, "/dashboard", external_user_id="u1") == "dashboard text"
    assert await processor._dispatch(service, "/policies", external_user_id="u1") == "policies text"
    assert await processor._dispatch(service, "/followups", external_user_id="u1") == "followups text"
    assert await processor._dispatch(service, "/renewals", external_user_id="u1") == "renewals text"
    service.renewals_summary.assert_awaited_with()


@pytest.mark.asyncio
async def test_processor_returns_fallback_for_unknown_text():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)

    reply = await processor._dispatch(service, "totally unknown request xyz", external_user_id="u1")

    assert "I didn't understand that request" in reply
    assert "Show dashboard" in reply
    assert "Or send /help." in reply
    assert "/dashboard - Insurance KPI summary" not in reply


@pytest.mark.asyncio
async def test_processor_routes_create_policy():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.create_policy = AsyncMock(return_value="created")

    reply = await processor._dispatch(
        service,
        "Create a Car policy for Kumar expiring July 10",
        external_user_id="u1",
    )

    assert reply == "created"
    service.create_policy.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_routes_log_followup():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.log_followup = AsyncMock(return_value="logged")

    reply = await processor._dispatch(service, "Log a follow-up for Priya in 3 days", external_user_id="u1")

    assert reply == "logged"
    service.log_followup.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_routes_mark_policy_renewed():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.start_policy_renewal = AsyncMock(return_value="renewal prompt")

    reply = await processor._dispatch(service, "Mark Ian's policy renewed", external_user_id="user-42")

    assert reply == "renewal prompt"
    service.start_policy_renewal.assert_awaited_once_with(
        customer_name="Ian",
        external_user_id="user-42",
    )


@pytest.mark.asyncio
async def test_processor_routes_policy_renewed_for_phrase():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.start_policy_renewal = AsyncMock(return_value="renewal prompt")

    reply = await processor._dispatch(service, "Policy renewed for Ravi", external_user_id="user-42")

    assert reply == "renewal prompt"
    service.start_policy_renewal.assert_awaited_once_with(
        customer_name="Ravi",
        external_user_id="user-42",
    )


@pytest.mark.asyncio
async def test_processor_routes_natural_language_dashboard():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.dashboard_summary = AsyncMock(return_value="dashboard data")

    reply = await processor._dispatch(service, "show dashboard", external_user_id="u1")

    assert reply == "dashboard data"
    service.dashboard_summary.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_routes_natural_language_policies():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.policies_summary = AsyncMock(return_value="policies data")

    reply = await processor._dispatch(service, "  POLICIES  ", external_user_id="u1")

    assert reply == "policies data"
    service.policies_summary.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_routes_natural_language_renewals():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.renewals_summary = AsyncMock(return_value="renewals data")

    reply = await processor._dispatch(service, "upcoming renewals", external_user_id="u1")

    assert reply == "renewals data"
    service.renewals_summary.assert_awaited_with()


@pytest.mark.asyncio
async def test_processor_routes_natural_language_followups():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.execute_menu_action = AsyncMock(return_value="followups data")

    reply = await processor._dispatch(service, "pending follow-ups", external_user_id="u1")

    assert reply == "followups data"
    service.execute_menu_action.assert_awaited_once_with("followups.pending")


@pytest.mark.asyncio
async def test_processor_routes_natural_language_active_policies():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.execute_menu_action = AsyncMock(return_value="active list")

    reply = await processor._dispatch(service, "show active policies", external_user_id="u1")

    assert reply == "active list"
    service.execute_menu_action.assert_awaited_once_with("policies.active")


@pytest.mark.asyncio
async def test_processor_routes_expiring_policies_days_query():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)
    service.expiring_policies_within_days = AsyncMock(return_value="expiring list")

    reply = await processor._dispatch(
        service,
        "show expiring policies in next 5 days",
        external_user_id="u1",
    )

    assert reply == "expiring list"
    service.expiring_policies_within_days.assert_awaited_once_with(days=5)


@pytest.mark.asyncio
async def test_processor_handles_greeting():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)

    from app.integrations.telegram.handlers import format_greeting_text

    hello_reply = await processor._dispatch(service, "hello", external_user_id="u1")
    hi_reply = await processor._dispatch(service, "hi", external_user_id="u1")
    hey_reply = await processor._dispatch(service, "Hey", external_user_id="u1")

    assert hello_reply == format_greeting_text("hello")
    assert hi_reply == format_greeting_text("hi")
    assert hey_reply == format_greeting_text("hey")
    service.help_message.assert_not_called()


@pytest.mark.asyncio
async def test_greeting_handler_runs_before_fallback():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)

    reply = await processor._dispatch(service, "hi", external_user_id="u1")

    assert "👋 Hi!" in reply
    assert "I didn't understand that request" not in reply
    service.help_message.assert_not_called()
    service.dashboard_summary.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payload_greeting_before_build_reply(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    build_reply = AsyncMock(return_value="fallback should not run")
    monkeypatch.setattr(processor, "_build_reply", build_reply)

    payload = {
        "message": {
            "text": "hey",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    reply = await processor.handle_payload(payload)

    assert reply is not None
    assert "👋 Hey!" in reply
    build_reply.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payload_navigation_before_fallback(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    build_reply = AsyncMock(return_value="dashboard data")
    monkeypatch.setattr(processor, "_build_reply", build_reply)

    payload = {
        "message": {
            "text": "Show dashboard",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    reply = await processor.handle_payload(payload)

    assert reply == "dashboard data"
    build_reply.assert_awaited_once_with(
        text="/dashboard",
        external_user_id="42",
        external_chat_id="1001",
        display_name="Test",
        organization_id=None,
    )


@pytest.mark.parametrize(
    ("text", "expected_command"),
    [
        ("dashboard", "/dashboard"),
        ("show dashboard", "/dashboard"),
        ("policies", "/policies"),
        ("renewals", "/renewals"),
        ("show renewals", "/renewals"),
        ("followups", "/followups"),
        ("show followups", "/followups"),
        ("show policies", "show policies"),
        ("show active policies", "show active policies"),
    ],
)
@pytest.mark.asyncio
async def test_handle_payload_natural_language_routes(text, expected_command, monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    build_reply = AsyncMock(return_value="ok")
    monkeypatch.setattr(processor, "_build_reply", build_reply)

    payload = {
        "message": {
            "text": text,
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    await processor.handle_payload(payload)

    command = build_reply.await_args.kwargs["text"]
    assert command == expected_command


@pytest.mark.asyncio
async def test_handle_payload_pending_renewal_accepts_date(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    complete = AsyncMock(return_value="✅ Policy Renewed\n\nCustomer: Ian")
    monkeypatch.setattr(processor, "_handle_pending_renewal_date", complete)

    renewal_context_store._pending["42"] = MagicMock()

    payload = {
        "message": {
            "text": "03-Jun-2027",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    reply = await processor.handle_payload(payload)

    assert "Policy Renewed" in reply
    complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_payload_pending_renewal_clears_on_slash_command(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    complete = AsyncMock(return_value="should not run")
    build_reply = AsyncMock(return_value="help text")
    monkeypatch.setattr(processor, "_handle_pending_renewal_date", complete)
    monkeypatch.setattr(processor, "_build_reply", build_reply)

    renewal_context_store._pending["42"] = MagicMock()

    payload = {
        "message": {
            "text": "/help",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    await processor.handle_payload(payload)

    assert renewal_context_store.get("42") is None
    complete.assert_not_called()
    build_reply.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_callback_opens_dashboard_menu():
    processor = TelegramUpdateProcessor(auto_reply=False)
    payload = {
        "callback_query": {
            "id": "cb-1",
            "data": CB_MAIN_DASHBOARD,
            "from": {"id": 42, "first_name": "Test"},
            "message": {"message_id": 99, "chat": {"id": 1001}},
        }
    }

    result = await processor.handle_callback_payload(payload)

    assert isinstance(result, HandlerReply)
    assert "Dashboard" in result.text
    assert result.menu == MenuKind.DASHBOARD
    assert menu_context_store.get("42") == MenuKind.DASHBOARD


@pytest.mark.asyncio
async def test_handle_callback_executes_kpi_action(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=False)
    monkeypatch.setattr(
        processor,
        "_handle_menu_interaction",
        AsyncMock(return_value="dashboard kpi data"),
    )
    payload = {
        "callback_query": {
            "id": "cb-2",
            "data": CB_ACTION_KPI,
            "from": {"id": 42, "first_name": "Test"},
            "message": {"message_id": 100, "chat": {"id": 1001}},
        }
    }

    result = await processor.handle_callback_payload(payload)

    assert isinstance(result, HandlerReply)
    assert result.text == "dashboard kpi data"
    assert result.menu == MenuKind.DASHBOARD


@pytest.mark.asyncio
async def test_handle_callback_help():
    processor = TelegramUpdateProcessor(auto_reply=False)
    payload = {
        "callback_query": {
            "id": "cb-3",
            "data": CB_MAIN_HELP,
            "from": {"id": 7, "first_name": "Ada"},
            "message": {"message_id": 1, "chat": {"id": 2002}},
        }
    }

    with patch.object(processor, "_handle_menu_interaction", AsyncMock(return_value="help text")) as menu_action:
        result = await processor.handle_callback_payload(payload)

    assert isinstance(result, HandlerReply)
    assert result.text == "help text"
    assert result.menu == MenuKind.MAIN
    menu_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_returns_fallback_for_unknown_command():
    processor = TelegramUpdateProcessor(auto_reply=False)
    service = AsyncMock(spec=TelegramInsuranceCommandService)

    reply = await processor._dispatch(service, "/unknowncmd", external_user_id="u1")

    assert "I didn't understand that request" in reply
    assert "Or send /help." in reply


@pytest.mark.asyncio
async def test_processor_handles_callback_payload():
    processor = TelegramUpdateProcessor(auto_reply=False)
    payload = {
        "callback_query": {
            "id": "cb-1",
            "data": CB_MAIN_DASHBOARD,
            "from": {"id": 42, "first_name": "Test"},
            "message": {"message_id": 99, "chat": {"id": 1001}},
        }
    }

    result = await processor.handle_callback_payload(payload)

    assert isinstance(result, HandlerReply)
    assert "Dashboard" in result.text
    assert result.menu == MenuKind.DASHBOARD


@pytest.mark.asyncio
async def test_processor_callback_help():
    processor = TelegramUpdateProcessor(auto_reply=False)
    payload = {
        "callback_query": {
            "id": "cb-2",
            "data": CB_MAIN_HELP,
            "from": {"id": 7, "first_name": "Ada"},
            "message": {"message_id": 1, "chat": {"id": 2002}},
        }
    }

    with patch.object(processor, "_handle_menu_interaction", AsyncMock(return_value="help text")) as menu_action:
        result = await processor.handle_callback_payload(payload)

    assert isinstance(result, HandlerReply)
    assert result.text == "help text"
    assert result.menu == MenuKind.MAIN
    menu_action.assert_awaited_once()


@pytest.mark.parametrize(
    ("command_text", "reply", "expected"),
    [
        ("/start", WELCOME_TEXT, True),
        ("hi", "👋 Hi!\n\nWelcome to SIMI Insurance Assistant.\n\n🏠 Main Menu", True),
        ("hello", "👋 Hello!\n\nWelcome to SIMI Insurance Assistant.\n\n🏠 Main Menu", True),
        ("main menu", MAIN_MENU_REPLY, True),
        ("/help", "help text", False),
        ("show dashboard", "dashboard data", False),
        ("totally unknown", fallback_help_message(), False),
    ],
)
def test_should_attach_main_menu(command_text, reply, expected):
    assert should_attach_main_menu(command_text=command_text, reply=reply) is expected


@pytest.mark.asyncio
async def test_handle_payload_main_menu_returns_prompt():
    processor = TelegramUpdateProcessor(auto_reply=False)

    payload = {
        "message": {
            "text": "main menu",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    reply = await processor.handle_payload(payload)

    assert reply == MAIN_MENU_REPLY


@pytest.mark.asyncio
async def test_handle_payload_main_menu_sends_keyboard_when_auto_reply(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=True, token="test-token")
    send_reply = AsyncMock()
    monkeypatch.setattr(processor, "_send_telegram_reply", send_reply)

    payload = {
        "message": {
            "text": "main menu",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    await processor.handle_payload(payload)

    send_reply.assert_awaited_once()
    assert send_reply.await_args.kwargs["menu"] == MenuKind.MAIN


@pytest.mark.asyncio
async def test_handle_payload_unknown_message_no_keyboard(monkeypatch):
    processor = TelegramUpdateProcessor(auto_reply=True, token="test-token")
    send_reply = AsyncMock()
    build_reply = AsyncMock(return_value=fallback_help_message())
    monkeypatch.setattr(processor, "_send_telegram_reply", send_reply)
    monkeypatch.setattr(processor, "_build_reply", build_reply)

    payload = {
        "message": {
            "text": "gibberish xyz",
            "chat": {"id": 1001},
            "from": {"id": 42, "first_name": "Test"},
        }
    }

    await processor.handle_payload(payload)

    send_reply.assert_awaited_once()
    assert send_reply.await_args.kwargs["menu"] is False
