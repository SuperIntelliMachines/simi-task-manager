"""General Reminder Definitions — org-level reminder rules for Reminder Management.

Separate from the entity-scoped Reminder Engine (`reminder_configs` /
`reminder_instances`). Definitions describe *what* to remind; a later phase can
expand them into engine configs per entity without changing those tables.
"""

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
    Integer,
    String,
    Text,
    Uuid,
    func,
    true,
)

from app.core.database import Base
from app.core.enums import ReminderAnchorType, ReminderOffsetDirection


class ReminderDefinition(Base):
    """Org-scoped general reminder definition (Reminder Management feature)."""

    __tablename__ = "reminder_definitions"
    __table_args__ = (
        CheckConstraint(
            f"trigger_type IN ('{ReminderAnchorType.DATE.value}', '{ReminderAnchorType.WORKFLOW.value}')",
            name="ck_reminder_definitions_trigger_type",
        ),
        CheckConstraint(
            f"offset_direction IN ('{ReminderOffsetDirection.BEFORE.value}', '{ReminderOffsetDirection.AFTER.value}')",
            name="ck_reminder_definitions_offset_direction",
        ),
        Index("ix_reminder_definitions_organization_id", "organization_id"),
        Index("ix_reminder_definitions_module_key", "module_key"),
        Index(
            "ix_reminder_definitions_trigger_type_key",
            "trigger_type",
            "trigger_key",
        ),
        Index("ix_reminder_definitions_is_active", "is_active"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.id"),
        nullable=False,
    )
    module_key = Column(String(50), nullable=False)
    reminder_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(
        String(20),
        nullable=False,
        default=ReminderAnchorType.DATE.value,
        server_default=ReminderAnchorType.DATE.value,
    )
    trigger_key = Column(String(100), nullable=False)
    offset_value = Column(Integer, nullable=False)
    offset_unit = Column(String(20), nullable=False, default="days", server_default="days")
    offset_direction = Column(
        String(20),
        nullable=False,
        default=ReminderOffsetDirection.BEFORE.value,
        server_default=ReminderOffsetDirection.BEFORE.value,
    )
    recipient_type = Column(String(50), nullable=False)
    recipient_value = Column(JSON, nullable=False, default=list, server_default="[]")
    channels = Column(JSON, nullable=False, default=list, server_default="[]")
    template_key = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
