"""Write helpers for Reminder History execution logs."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_history import (
    REMINDER_HISTORY_STATUS_FAILED,
    REMINDER_HISTORY_STATUS_SENT,
    REMINDER_HISTORY_STATUS_SKIPPED,
    ReminderHistory,
)

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ReminderHistoryService:
    """Persist one reminder_history row per delivery attempt."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_attempt(
        self,
        *,
        organization_id: int,
        reminder_id: uuid.UUID | None,
        template_id: uuid.UUID | None,
        created_by: int,
        reminder_title: str,
        channel: str,
        recipient: str,
        status: str,
        provider_message_id: str | None = None,
        error_message: str | None = None,
        executed_at: datetime | None = None,
    ) -> ReminderHistory | None:
        """
        Insert a history row.

        Never raises to callers — history write failures are logged only so
        reminder delivery is not interrupted.
        """
        status_normalized = (status or "").strip().upper()
        if status_normalized not in {
            REMINDER_HISTORY_STATUS_SENT,
            REMINDER_HISTORY_STATUS_FAILED,
            REMINDER_HISTORY_STATUS_SKIPPED,
        }:
            logger.warning(
                "[ReminderHistory] Invalid status=%s; coercing to FAILED",
                status,
            )
            status_normalized = REMINDER_HISTORY_STATUS_FAILED

        when = executed_at or utcnow_naive()
        try:
            row = ReminderHistory(
                organization_id=int(organization_id),
                reminder_id=reminder_id,
                template_id=template_id,
                created_by=int(created_by),
                reminder_title=(reminder_title or "").strip() or "Reminder",
                channel=(channel or "").strip().lower() or "unknown",
                recipient=(recipient or "").strip() or "-",
                status=status_normalized,
                provider_message_id=(provider_message_id or None),
                error_message=(error_message or None),
                executed_at=when,
                created_at=when,
            )
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
            return row
        except Exception:  # noqa: BLE001
            logger.exception(
                "[ReminderHistory] Failed to record attempt reminder_id=%s channel=%s status=%s",
                reminder_id,
                channel,
                status_normalized,
            )
            return None

    async def record_sent(self, **kwargs) -> ReminderHistory | None:
        return await self.record_attempt(status=REMINDER_HISTORY_STATUS_SENT, **kwargs)

    async def record_failed(self, **kwargs) -> ReminderHistory | None:
        return await self.record_attempt(status=REMINDER_HISTORY_STATUS_FAILED, **kwargs)

    async def record_skipped(self, **kwargs) -> ReminderHistory | None:
        return await self.record_attempt(status=REMINDER_HISTORY_STATUS_SKIPPED, **kwargs)
