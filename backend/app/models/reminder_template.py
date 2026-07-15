"""Reminder Templates — org-scoped message templates for Personal Reminders."""

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

REMINDER_TEMPLATE_CHANNELS = frozenset({"email", "in_app", "sms", "telegram", "whatsapp"})
WHATSAPP_APPROVAL_STATUSES = frozenset(
    {"draft", "pending_approval", "approved", "rejected"}
)
WHATSAPP_APPROVAL_DRAFT = "draft"


class ReminderTemplate(Base):
    """Org-scoped reminder template (Reminder Management → Templates)."""

    __tablename__ = "reminder_templates"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'in_app', 'sms', 'telegram', 'whatsapp')",
            name="ck_reminder_templates_channel",
        ),
        CheckConstraint(
            "approval_status IS NULL OR approval_status IN "
            "('draft', 'pending_approval', 'approved', 'rejected')",
            name="ck_reminder_templates_approval_status",
        ),
        Index("ix_reminder_templates_organization_id", "organization_id"),
        Index("ix_reminder_templates_channel", "channel"),
        Index("ix_reminder_templates_is_active", "is_active"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.id"),
        nullable=False,
    )
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    channel = Column(String(32), nullable=False)
    subject = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    variables = Column(JSON, nullable=False, default=list, server_default="[]")
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    whatsapp_template_name = Column(String(255), nullable=True)
    approval_status = Column(String(32), nullable=True)
    meta_template_id = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
