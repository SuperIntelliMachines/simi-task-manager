import hashlib
import hmac
import json

import httpx
import pytest

from app.channels.whatsapp_adapter import WhatsAppAdapter
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_whatsapp_verification_challenge_returns_response():
    adapter = WhatsAppAdapter(verify_token="verify-123", app_secret="")
    verified, challenge = adapter.verify_webhook(
        method="GET",
        query_params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-123",
            "hub.challenge": "42",
        },
        headers={},
        body=b"",
    )

    assert verified is True
    assert challenge == "42"


@pytest.mark.asyncio
async def test_whatsapp_inbound_stop_can_be_normalized():
    adapter = WhatsAppAdapter(verify_token="", app_secret="")
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"id": "wamid-1", "from": "91999", "type": "text", "text": {"body": "STOP"}}],
                            "contacts": [{"wa_id": "91999"}],
                        }
                    }
                ]
            }
        ]
    }

    normalized = adapter.normalize_inbound_payload(payload)
    assert normalized.text == "STOP"
    assert normalized.external_user_id == "91999"


@pytest.mark.asyncio
async def test_whatsapp_signature_verification():
    secret = "app-secret"
    adapter = WhatsAppAdapter(verify_token="", app_secret=secret)

    payload = {"hello": "world"}
    raw = json.dumps(payload).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    verified, _ = adapter.verify_webhook(
        method="POST",
        query_params={},
        headers={"x-hub-signature-256": signature},
        body=raw,
    )
    assert verified is True


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_calls_meta_api(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://graph.facebook.com/v22.0/123456/messages")
        assert request.headers.get("Authorization") == "Bearer test-token"
        body = json.loads(request.content.decode("utf-8"))
        assert body == {
            "messaging_product": "whatsapp",
            "to": "919876543210",
            "type": "template",
            "template": {"name": "welcome", "language": {"code": "en"}},
        }
        return httpx.Response(200, json={"messages": [{"id": "wamid.HBgM..."},],})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={},
        recipient="919876543210",
        text="Hello",
    )
    assert message_id == "wamid.HBgM..."
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_raises_on_meta_error(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid recipient"}})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    with pytest.raises(RuntimeError, match="whatsapp api send failed status=400"):
        await adapter.send_outbound_message(
            connection_settings={},
            recipient="919876543210",
            text="Hello",
        )
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_welcome_static_template_has_no_components(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["template"]["name"] == "welcome"
        assert "components" not in body["template"]
        return httpx.Response(201, json={"messages": [{"id": "wamid.template.welcome"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={},
        recipient="919876543210",
        text="ignored-text-for-template",
        template_variables={
            "customer_name": "Uday",
            "entity_label": "Policy Renewal",
            "reminder_date": "30-07-2026 02:30 PM",
            "sender_name": "ABC Insurance",
        },
    )

    assert message_id == "wamid.template.welcome"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_policy_template_includes_four_body_params(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["template"]["name"] == "policy_renewal_reminder"
        assert body["template"]["language"] == {"code": "en_US"}
        assert body["template"]["components"] == [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Uday"},
                    {"type": "text", "text": "Policy Renewal"},
                    {"type": "text", "text": "30-07-2026 02:30 PM"},
                    {"type": "text", "text": "ABC Insurance"},
                ],
            }
        ]
        return httpx.Response(201, json={"messages": [{"id": "wamid.template.1"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "policy_renewal_reminder")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={},
        recipient="919876543210",
        text="ignored-text-for-template",
        template_variables={
            "customer_name": "Uday",
            "entity_label": "Policy Renewal",
            "reminder_date": "30-07-2026 02:30 PM",
            "sender_name": "ABC Insurance",
        },
    )

    assert message_id == "wamid.template.1"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_template_name_fallback_chain(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient
    seen_names: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        seen_names.append(body["template"]["name"])
        return httpx.Response(201, json={"messages": [{"id": f"wamid.{len(seen_names)}"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    await adapter.send_outbound_message(
        connection_settings={"templateName": "connection_template"},
        recipient="919876543210",
        text="Hello",
        template_name="arg_template",
    )
    await adapter.send_outbound_message(
        connection_settings={"templateName": "connection_template"},
        recipient="919876543210",
        text="Hello",
    )
    await adapter.send_outbound_message(
        connection_settings={},
        recipient="919876543210",
        text="Hello",
    )

    assert seen_names == ["arg_template", "connection_template", "welcome"]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_uses_env_language_en(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["template"]["language"] == {"code": "en"}
        return httpx.Response(201, json={"messages": [{"id": "wamid.lang.en"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={"language": "en_US"},
        recipient="919876543210",
        text="Hello",
    )
    assert message_id == "wamid.lang.en"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_send_outbound_message_session_text_mode(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body == {
            "messaging_product": "whatsapp",
            "to": "919876543210",
            "type": "text",
            "text": {"body": "Your policy renewal is due soon."},
        }
        return httpx.Response(201, json={"messages": [{"id": "wamid.session.text"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("USE_WHATSAPP_SESSION_TEXT", "true")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={},
        recipient="919876543210",
        text="Your policy renewal is due soon.",
    )
    assert message_id == "wamid.session.text"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_session_text_env_can_be_overridden_per_send(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["type"] == "template"
        assert body["template"]["name"] == "policy_renewal_reminder"
        assert body["template"]["language"] == {"code": "en_US"}
        return httpx.Response(201, json={"messages": [{"id": "wamid.template.override"}]})

    transport = httpx.MockTransport(handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = original_async_client(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_NAME", "welcome")
    monkeypatch.setenv("USE_WHATSAPP_SESSION_TEXT", "true")
    monkeypatch.setattr("app.channels.whatsapp_adapter.httpx.AsyncClient", MockClient)

    message_id = await adapter.send_outbound_message(
        connection_settings={"use_whatsapp_session_text": False},
        recipient="919876543210",
        text="ignored-text-for-template",
        template_name="policy_renewal_reminder",
        template_language="en_US",
        template_variables={
            "customer_name": "Uday",
            "entity_label": "Policy Renewal",
            "reminder_date": "30-07-2026 02:30 PM",
            "sender_name": "ABC Insurance",
        },
    )
    assert message_id == "wamid.template.override"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_session_text_mode_requires_body(monkeypatch):
    adapter = WhatsAppAdapter()
    get_settings.cache_clear()
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("USE_WHATSAPP_SESSION_TEXT", "true")

    with pytest.raises(ValueError, match="missing whatsapp session text body"):
        await adapter.send_outbound_message(
            connection_settings={},
            recipient="919876543210",
            text="   ",
        )
    get_settings.cache_clear()
