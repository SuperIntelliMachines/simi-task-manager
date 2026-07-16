"""Tests for PersonalReminderProcessorService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sqlalchemy import delete

from app.models.personal_reminder import (
    PERSONAL_REMINDER_STATUS_FAILED,
    PERSONAL_REMINDER_STATUS_PENDING,
    PERSONAL_REMINDER_STATUS_SENT,
    PersonalReminder,
)
from app.models.reminder_template import ReminderTemplate
from app.services.personal_reminder_processor import PersonalReminderProcessorService
from tests.helpers.auth import seed_org, seed_user


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture(autouse=True)
async def clear_personal_reminders(async_session):
    await async_session.execute(delete(PersonalReminder))
    await async_session.execute(delete(ReminderTemplate))
    await async_session.commit()


async def _seed_personal_reminder(
    async_session,
    *,
    org_id: int,
    user_id: int,
    scheduled_at: datetime | None = None,
    status: str = PERSONAL_REMINDER_STATUS_PENDING,
    is_active: bool = True,
    channels: list[str] | None = None,
    custom_message: str | None = "Hello from personal reminder",
    template_id=None,
    email: str | None = "user@example.com",
    whatsapp_number: str | None = None,
    title: str = "Test Reminder",
) -> PersonalReminder:
    now = utcnow_naive()
    row = PersonalReminder(
        organization_id=org_id,
        created_by=user_id,
        title=title,
        description="Desc",
        scheduled_at=scheduled_at or (now - timedelta(minutes=5)),
        channels=channels or ["email"],
        email=email,
        whatsapp_number=whatsapp_number,
        custom_message=custom_message,
        template_id=template_id,
        status=status,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    async_session.add(row)
    await async_session.commit()
    await async_session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_process_due_reminders_marks_sent(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT
    assert refreshed.sent_at is not None


@pytest.mark.asyncio
async def test_process_due_reminders_skips_future_and_inactive(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        scheduled_at=utcnow_naive() + timedelta(hours=1),
    )
    await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        is_active=False,
    )
    await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        status=PERSONAL_REMINDER_STATUS_SENT,
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 0, "sent": 0, "failed": 0}


@pytest.mark.asyncio
async def test_process_due_reminders_marks_failed_on_channel_error(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
    )

    async def _fail_send(self, **kwargs):
        row = SimpleNamespace(status="failed")
        row.provider_error = "provider unavailable"
        return row

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _fail_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 0, "failed": 1}

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_FAILED
    assert refreshed.sent_at is None


@pytest.mark.asyncio
async def test_process_due_reminders_uses_template_body(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    now = utcnow_naive()
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name="Email Template",
        channel="email",
        subject="Subject from template",
        title=None,
        body="Body from template",
        variables=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        template_id=template.id,
        custom_message=None,
    )

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats["sent"] == 1
    assert captured["text"] == "Body from template"
    assert captured["connection_settings"] == {"subject": "Subject from template"}


@pytest.mark.asyncio
async def test_internal_process_endpoint(async_session, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.core.config import get_settings
    from app.core.database import get_db_session
    from app.main import app

    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    await _seed_personal_reminder(async_session, org_id=org.id, user_id=user.id)

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    settings = get_settings()
    settings.scheduler_secret = "test-scheduler-secret"

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/personal-reminders/process",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"processed": 1, "sent": 1, "failed": 0}


@pytest.mark.asyncio
async def test_whatsapp_approved_template_sends_named_variables(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(
        async_session,
        organization_id=org.id,
        email="uday.kumar@example.com",
    )
    now = utcnow_naive()
    scheduled_at = now - timedelta(minutes=5)
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name="Policy Renewal",
        channel="whatsapp",
        subject=None,
        title=None,
        body="Hi {{1}}, reminder for {{2}} on {{3}}. Thanks, {{4}}",
        variables=["customer_name", "policy_name", "reminder_date", "company_name"],
        is_active=True,
        whatsapp_template_name="policy_renewal_reminder",
        approval_status="approved",
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=["whatsapp"],
        whatsapp_number="+919876543210",
        email=None,
        template_id=template.id,
        custom_message=None,
        title="Interview Reminder",
        scheduled_at=scheduled_at,
    )

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["channel"] == "whatsapp"
    assert captured["template_name"] == "policy_renewal_reminder"
    assert captured["connection_settings"]["use_whatsapp_session_text"] is False
    assert captured["connection_settings"]["templateLayout"] == {
        "components": [
            {
                "type": "body",
                "param_keys": [
                    "customer_name",
                    "policy_name",
                    "reminder_date",
                    "company_name",
                ],
            }
        ]
    }
    assert captured["template_variables"] == {
        "customer_name": "Uday Kumar",
        "policy_name": "Interview Reminder",
        "reminder_date": scheduled_at.strftime("%d %b %Y %I:%M %p"),
        "company_name": "SIMI AI Task Manager",
    }
    assert "entity_label" not in captured["template_variables"]
    assert "sender_name" not in captured["template_variables"]
    assert len(captured["template_variables"]) == 4

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT


@pytest.mark.asyncio
async def test_policy_renewal_reminder_resolves_all_four_even_with_mismatched_variable_names(
    async_session, monkeypatch
):
    """Regression: DB variable names like policy_name/company_name must still yield 4 Meta params."""
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id, email="alex@example.com")
    now = utcnow_naive()
    scheduled_at = now - timedelta(minutes=1)
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name="WA Renewal",
        channel="whatsapp",
        body="body",
        variables=["customer_name", "policy_name", "reminder_date", "company_name"],
        is_active=True,
        whatsapp_template_name="policy_renewal_reminder",
        approval_status="approved",
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=["whatsapp"],
        whatsapp_number="+919999999999",
        email=None,
        template_id=template.id,
        custom_message=None,
        title="Car Insurance Policy",
        scheduled_at=scheduled_at,
    )

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats["sent"] == 1
    variables = captured["template_variables"]
    assert variables == {
        "customer_name": "Alex",
        "policy_name": "Car Insurance Policy",
        "reminder_date": scheduled_at.strftime("%d %b %Y %I:%M %p"),
        "company_name": "SIMI AI Task Manager",
    }


@pytest.mark.asyncio
async def test_process_due_email_reminder_through_channel_service(async_session, monkeypatch):
    """Email personal reminders must succeed when ChannelService forwards template_* kwargs."""
    from app.channels.email_adapter import EmailAdapter
    from app.services.email_service import EmailService

    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=["email"],
        email="holder@example.com",
        title="Interview Reminder",
        custom_message="Please join the interview tomorrow.",
    )

    sent: dict[str, object] = {}

    class FakeEmailService(EmailService):
        async def send_email(self, *, to, subject, text, html=None):
            sent.update({"to": to, "subject": subject, "text": text, "html": html})
            return "smtp-id-email-1"

    async def _channel_send_like_production(self, **kwargs):
        # Mirror ChannelService: always forward template_* to the adapter.
        adapter = EmailAdapter(
            FakeEmailService(
                smtp_host="smtp.gmail.com",
                smtp_username="noreply@example.com",
                smtp_password="secret",
                from_email="noreply@example.com",
            )
        )
        provider_id = await adapter.send_outbound_message(
            connection_settings=kwargs.get("connection_settings") or {},
            recipient=kwargs["recipient"],
            text=kwargs["text"],
            template_name=kwargs.get("template_name"),
            template_language=kwargs.get("template_language"),
            template_variables=kwargs.get("template_variables"),
        )
        assert provider_id == "smtp-id-email-1"
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _channel_send_like_production,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}
    assert sent == {
        "to": "holder@example.com",
        "subject": "Interview Reminder",
        "text": "Please join the interview tomorrow.",
        "html": None,
    }

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT


@pytest.mark.asyncio
async def test_due_selection_uses_db_now_not_python_utc(async_session, monkeypatch):
    """Local wall-clock scheduled_at must be selected when due vs application/DB now.

    Regression: comparing against Python UTC left IST wall-clock schedules several hours late.
    """
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)

    # Application/DB "now" in wall-clock terms (e.g. 15:40 local).
    app_now = datetime(2026, 7, 15, 15, 40, 0)
    # Same instant expressed as UTC would be ~10:10 — old bug used this and missed local 15:30.
    python_utc = datetime(2026, 7, 15, 10, 10, 0)
    local_scheduled_at = datetime(2026, 7, 15, 15, 30, 0)

    assert local_scheduled_at <= app_now
    assert not (local_scheduled_at <= python_utc)

    async def _fake_db_now(session):
        return app_now

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.fetch_db_now",
        _fake_db_now,
    )
    monkeypatch.setattr(
        "app.services.personal_reminder_processor.utcnow_naive",
        lambda: python_utc,
    )

    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        scheduled_at=local_scheduled_at,
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT
    assert refreshed.sent_at == app_now


@pytest.mark.asyncio
async def test_multi_channel_resolves_channel_specific_content(async_session, monkeypatch):
    """Selecting one definition must not reuse WhatsApp body for In-App."""
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id, email="priya@example.com")
    now = utcnow_naive()
    definition_name = "Interview Reminder"

    wa_template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name=definition_name,
        channel="whatsapp",
        body="Hi {{1}}, this is {{2}} on {{3}}. — {{4}}",
        variables=[],
        is_active=True,
        whatsapp_template_name="policy_renewal_reminder",
        approval_status="approved",
        created_at=now,
        updated_at=now,
    )
    in_app_template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name=definition_name,
        channel="in_app",
        title="Interview",
        body="Hi {customer_name}, your interview reminder is ready.",
        variables=["customer_name"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add_all([wa_template, in_app_template])
    await async_session.commit()

    # Store WhatsApp variant id (as users often did before) — resolution is by name.
    reminder = await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=["whatsapp", "in_app"],
        whatsapp_number="+919876543210",
        email=None,
        template_id=wa_template.id,
        custom_message=None,
        title="Interview Reminder",
    )

    captured: list[dict[str, object]] = []

    async def _ok_send(self, **kwargs):
        captured.append(dict(kwargs))
        return SimpleNamespace(status="sent", external_provider_message_id="msg-1")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}
    assert len(captured) == 2

    by_channel = {str(item["channel"]): item for item in captured}
    assert by_channel["whatsapp"]["template_name"] == "policy_renewal_reminder"
    assert by_channel["whatsapp"]["template_variables"]["customer_name"] == "Priya"

    in_app_text = str(by_channel["in_app"]["text"])
    assert "{{1}}" not in in_app_text
    assert "{{2}}" not in in_app_text
    assert in_app_text == "Hi Priya, your interview reminder is ready."
    assert by_channel["in_app"]["connection_settings"]["title"] == "Interview"


@pytest.mark.asyncio
async def test_missing_channel_variant_fails(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    now = utcnow_naive()
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name="WA Only",
        channel="whatsapp",
        body="Hi {{1}}",
        variables=[],
        is_active=True,
        whatsapp_template_name="policy_renewal_reminder",
        approval_status="approved",
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    await _seed_personal_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=["whatsapp", "in_app"],
        whatsapp_number="+919876543210",
        email=None,
        template_id=template.id,
        custom_message=None,
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats["failed"] == 1
    assert stats["sent"] == 0
