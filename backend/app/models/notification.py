"""Generic in-app notifications (module-agnostic)."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.core.database import Base

NOTIFICATION_STATUS_UNREAD = "UNREAD"
NOTIFICATION_STATUS_READ = "READ"
NOTIFICATION_STATUSES = frozenset({NOTIFICATION_STATUS_UNREAD, NOTIFICATION_STATUS_READ})


class Notification(Base):
    """Platform-wide in-app notification inbox row.

    Scoped by organization_id + user_id. Linked to any module via
    entity_type / entity_id — never Claims- or Insurance-specific columns.
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    reminder_instance_id = Column(
        Integer,
        ForeignKey("reminder_instances.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(32), nullable=False, default="normal", server_default="normal")
    status = Column(String(20), nullable=False, default=NOTIFICATION_STATUS_UNREAD, server_default=NOTIFICATION_STATUS_UNREAD)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    read_at = Column(DateTime, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
