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
    )

    assert provider_id == "smtp-id-99"
    assert sent["to"] == "holder@example.com"
    assert sent["subject"] == "Policy reminder"
    assert sent["text"] == "Premium due soon"
