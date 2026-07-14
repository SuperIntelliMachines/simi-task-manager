import pytest

from app.services.email_service import EmailDeliveryError, EmailService


@pytest.mark.asyncio
async def test_email_service_requires_configuration():
    service = EmailService(
        smtp_host="",
        smtp_username="",
        smtp_password="",
        from_email="",
    )
    assert service.is_configured() is False
    with pytest.raises(EmailDeliveryError, match="not configured"):
        await service.send_email(to="user@example.com", subject="Hi", text="Body")


@pytest.mark.asyncio
async def test_email_service_send_success(monkeypatch):
    service = EmailService(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username="reminders@example.com",
        smtp_password="app-password",
        from_email="SIMI <reminders@example.com>",
    )
    captured: dict = {}

    def fake_send_smtp_email(*, recipient, subject, text, html):
        captured.update(
            {
                "recipient": recipient,
                "subject": subject,
                "text": text,
                "html": html,
            }
        )
        return "smtp-msg-123"

    monkeypatch.setattr(service, "_send_smtp_email", fake_send_smtp_email)

    message_id = await service.send_email(
        to="customer@example.com",
        subject="Premium payment reminder",
        text="Your premium is due.",
    )

    assert message_id == "smtp-msg-123"
    assert captured["recipient"] == "customer@example.com"
    assert captured["subject"] == "Premium payment reminder"
    assert captured["text"] == "Your premium is due."
    assert captured["html"] is None
