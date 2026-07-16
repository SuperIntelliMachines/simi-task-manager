"""Reminder History — one row per reminder channel execution attempt."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)

from app.core.database import Base

REMINDER_HISTORY_STATUS_SENT = "SENT"
REMINDER_HISTORY_STATUS_FAILED = "FAILED"
REMINDER_HISTORY_STATUS_SKIPPED = "SKIPPED"
REMINDER_HISTORY_STATUSES = frozenset(
    {
        REMINDER_HISTORY_STATUS_SENT,
        REMINDER_HISTORY_STATUS_FAILED,
        REMINDER_HISTORY_STATUS_SKIPPED,
    }
)


class ReminderHistory(Base):
    """Execution attempt log for reminder channel sends (success or failure)."""

    __tablename__ = "reminder_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SENT', 'FAILED', 'SKIPPED')",
            name="ck_reminder_history_status",
        ),
        Index("ix_reminder_history_organization_id", "organization_id"),
        Index("ix_reminder_history_reminder_id", "reminder_id"),
        Index("ix_reminder_history_status", "status"),
        Index("ix_reminder_history_channel", "channel"),
        Index("ix_reminder_history_executed_at", "executed_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.id"),
        nullable=False,
    )
    reminder_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("personal_reminders.id"),
        nullable=True,
    )
    template_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("reminder_templates.id"),
        nullable=True,
    )
    created_by = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    reminder_title = Column(String(255), nullable=False)
    channel = Column(String(32), nullable=False)
    recipient = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
