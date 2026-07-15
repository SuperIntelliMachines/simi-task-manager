"""Personal Reminders — user-owned reminders independent of the Generic Reminder Engine."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    true,
)

from app.core.database import Base

PERSONAL_REMINDER_STATUS_PENDING = "PENDING"
PERSONAL_REMINDER_STATUS_SENT = "SENT"
PERSONAL_REMINDER_STATUS_FAILED = "FAILED"
PERSONAL_REMINDER_STATUS_CANCELLED = "CANCELLED"
PERSONAL_REMINDER_STATUSES = frozenset(
    {
        PERSONAL_REMINDER_STATUS_PENDING,
        PERSONAL_REMINDER_STATUS_SENT,
        PERSONAL_REMINDER_STATUS_FAILED,
        PERSONAL_REMINDER_STATUS_CANCELLED,
    }
)


class PersonalReminder(Base):
    """Org-scoped personal reminder owned by ``created_by``.

    Completely separate from Reminder Engine tables
    (`reminder_configs` / `reminder_instances` / `reminder_definitions`).
    """

    __tablename__ = "personal_reminders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED')",
            name="personal_reminders_status_check",
        ),
        Index("idx_personal_reminders_org", "organization_id"),
        Index("idx_personal_reminders_created_by", "created_by"),
        Index("idx_personal_reminders_scheduled_at", "scheduled_at"),
        Index("idx_personal_reminders_status", "status"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.id"),
        nullable=False,
    )
    created_by = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    channels = Column(JSON, nullable=False, default=list, server_default="[]")
    email = Column(String(255), nullable=True)
    mobile_number = Column(String(20), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)
    template_id = Column(Uuid(as_uuid=True), nullable=True)
    custom_message = Column(Text, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=PERSONAL_REMINDER_STATUS_PENDING,
        server_default=PERSONAL_REMINDER_STATUS_PENDING,
    )
    sent_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
