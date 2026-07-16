import pytest

from app.channels.email_adapter import EmailAdapter
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_email_adapter_sends_with_subject_from_connection_settings():
    sent: dict = {}

    class FakeEmailService(EmailService):
        async def send_email(self, *, to, subject, text, html=None):
            sent.update({"to": to, "subject": subject, "text": text, "html": html})
            return "smtp-id-99"

    adapter = EmailAdapter(
        FakeEmailService(
            smtp_host="smtp.gmail.com",
            smtp_username="noreply@example.com",
            smtp_password="secret",
            from_email="noreply@example.com",
        )
    )
    provider_id = await adapter.send_outbound_message(
        connection_settings={"subject": "Policy reminder"},
        recipient="holder@example.com",
        text="Premium due soon",
        template_name=None,
        template_language=None,
        template_variables=None,
    )

    assert provider_id == "smtp-id-99"
    assert sent["to"] == "holder@example.com"
    assert sent["subject"] == "Policy reminder"
    assert sent["text"] == "Premium due soon"


@pytest.mark.asyncio
async def test_email_adapter_ignores_template_language_kwarg_from_channel_service():
    """ChannelService always forwards template_*; Email must accept and ignore them."""
    sent: dict = {}

    class FakeEmailService(EmailService):
        async def send_email(self, *, to, subject, text, html=None):
            sent.update({"to": to, "subject": subject, "text": text})
            return "smtp-id-100"

    adapter = EmailAdapter(
        FakeEmailService(
            smtp_host="smtp.gmail.com",
            smtp_username="noreply@example.com",
            smtp_password="secret",
            from_email="noreply@example.com",
        )
    )
    provider_id = await adapter.send_outbound_message(
        connection_settings={"subject": "Personal reminder"},
        recipient="user@example.com",
        text="Hello",
        template_name="unused",
        template_language="en_US",
        template_variables={"customer_name": "Uday"},
    )
    assert provider_id == "smtp-id-100"
    assert sent["to"] == "user@example.com"
    assert sent["subject"] == "Personal reminder"
    assert sent["text"] == "Hello"
