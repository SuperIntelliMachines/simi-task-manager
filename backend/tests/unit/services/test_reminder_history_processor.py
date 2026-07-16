"""Tests for Reminder History write integration in PersonalReminderProcessor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.models.personal_reminder import (
    PERSONAL_REMINDER_STATUS_FAILED,
    PERSONAL_REMINDER_STATUS_PENDING,
    PERSONAL_REMINDER_STATUS_SENT,
    PersonalReminder,
)
from app.models.reminder_history import (
    REMINDER_HISTORY_STATUS_FAILED,
    REMINDER_HISTORY_STATUS_SENT,
    REMINDER_HISTORY_STATUS_SKIPPED,
    ReminderHistory,
)
from app.models.reminder_template import ReminderTemplate
from app.services.personal_reminder_processor import PersonalReminderProcessorService
from app.services.reminder_history_service import ReminderHistoryService
from tests.helpers.auth import seed_org, seed_user


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture(autouse=True)
async def clear_reminder_tables(async_session):
    await async_session.execute(delete(ReminderHistory))
    await async_session.execute(delete(PersonalReminder))
    await async_session.execute(delete(ReminderTemplate))
    await async_session.commit()


async def _seed_reminder(
    async_session,
    *,
    org_id: int,
    user_id: int,
    channels: list[str] | None = None,
    email: str | None = "holder@example.com",
    whatsapp_number: str | None = None,
    custom_message: str | None = "Hello",
    title: str = "History Test Reminder",
    template_id=None,
    is_active: bool = True,
    status: str = PERSONAL_REMINDER_STATUS_PENDING,
    scheduled_at: datetime | None = None,
) -> PersonalReminder:
    now = utcnow_naive()
    row = PersonalReminder(
        organization_id=org_id,
        created_by=user_id,
        title=title,
        description=None,
        scheduled_at=scheduled_at or (now - timedelta(minutes=5)),
        channels=channels if channels is not None else ["email"],
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
async def test_history_service_records_attempt(async_session):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_reminder(async_session, org_id=org.id, user_id=user.id)

    service = ReminderHistoryService(async_session)
    row = await service.record_sent(
        organization_id=org.id,
        reminder_id=reminder.id,
        template_id=None,
        created_by=user.id,
        reminder_title=reminder.title,
        channel="email",
        recipient="holder@example.com",
        provider_message_id="smtp-1",
    )
    await async_session.commit()

    assert row is not None
    assert row.status == REMINDER_HISTORY_STATUS_SENT
    stored = (
        await async_session.execute(select(ReminderHistory).where(ReminderHistory.id == row.id))
    ).scalar_one()
    assert stored.provider_message_id == "smtp-1"
    assert stored.channel == "email"


@pytest.mark.asyncio
async def test_successful_send_writes_sent_history(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        title="Interview Reminder",
        email="agent@example.com",
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(
            status="sent",
            external_provider_message_id="msg-email-1",
        )

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}

    history = list((await async_session.execute(select(ReminderHistory))).scalars())
    assert len(history) == 1
    row = history[0]
    assert row.organization_id == org.id
    assert row.reminder_id == reminder.id
    assert row.template_id is None
    assert row.created_by == user.id
    assert row.reminder_title == "Interview Reminder"
    assert row.channel == "email"
    assert row.recipient == "agent@example.com"
    assert row.status == REMINDER_HISTORY_STATUS_SENT
    assert row.provider_message_id == "msg-email-1"
    assert row.error_message is None
    assert row.executed_at is not None

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT


@pytest.mark.asyncio
async def test_failed_send_writes_failed_history(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_reminder(async_session, org_id=org.id, user_id=user.id)

    async def _fail_send(self, **kwargs):
        row = SimpleNamespace(status="failed", external_provider_message_id=None)
        row.provider_error = "smtp unavailable"
        return row

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _fail_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 0, "failed": 1}

    history = list((await async_session.execute(select(ReminderHistory))).scalars())
    assert len(history) == 1
    row = history[0]
    assert row.status == REMINDER_HISTORY_STATUS_FAILED
    assert row.error_message == "smtp unavailable"
    assert row.channel == "email"
    assert row.recipient == "holder@example.com"
    assert row.reminder_id == reminder.id

    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_FAILED


@pytest.mark.asyncio
async def test_skipped_reminder_writes_skipped_history(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        channels=[],
        custom_message="unused",
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent", external_provider_message_id="should-not-send")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats["failed"] == 1
    assert stats["sent"] == 0

    history = list((await async_session.execute(select(ReminderHistory))).scalars())
    assert len(history) == 1
    row = history[0]
    assert row.status == REMINDER_HISTORY_STATUS_SKIPPED
    assert row.reminder_id == reminder.id
    assert row.channel == "-"
    assert "no channels" in (row.error_message or "").lower()


@pytest.mark.asyncio
async def test_history_includes_template_id_when_present(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    now = utcnow_naive()
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org.id,
        created_by=user.id,
        name="Email Body",
        channel="email",
        subject="Subject",
        title=None,
        body="Template body text",
        variables=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    reminder = await _seed_reminder(
        async_session,
        org_id=org.id,
        user_id=user.id,
        template_id=template.id,
        custom_message=None,
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent", external_provider_message_id="tmpl-1")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    await PersonalReminderProcessorService(async_session).process_due_reminders()
    row = (await async_session.execute(select(ReminderHistory))).scalar_one()
    assert row.template_id == template.id
    assert row.status == REMINDER_HISTORY_STATUS_SENT


@pytest.mark.asyncio
async def test_history_write_failure_does_not_break_send(async_session, monkeypatch):
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id)
    reminder = await _seed_reminder(async_session, org_id=org.id, user_id=user.id)

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent", external_provider_message_id="ok-1")

    async def _broken_record(self, **kwargs):
        raise RuntimeError("history table unavailable")

    monkeypatch.setattr(
        "app.services.personal_reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )
    monkeypatch.setattr(
        ReminderHistoryService,
        "record_attempt",
        _broken_record,
    )

    stats = await PersonalReminderProcessorService(async_session).process_due_reminders()
    assert stats == {"processed": 1, "sent": 1, "failed": 0}
    refreshed = await async_session.get(PersonalReminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == PERSONAL_REMINDER_STATUS_SENT
