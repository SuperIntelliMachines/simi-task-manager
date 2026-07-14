from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "external_provider_message_id",
            name="uq_outbound_messages_channel_provider_message",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=True)
    channel = Column(String(32), nullable=False)
    recipient = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    external_provider_message_id = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    actor_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    requested_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    reason = Column(Text, nullable=True)
    proposed_action = Column(JSON, nullable=False, default=dict)
    decision_notes = Column(Text, nullable=True)
    approved_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    rejected_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    decisioned_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    agent_invocation_id = Column(BigInteger, nullable=True)
    session_type = Column(String(64), nullable=False, default="clarification")
    status = Column(String(32), nullable=False, default="active")
    collected_fields = Column(JSON, nullable=False, default=dict)
    missing_fields = Column(JSON, nullable=False, default=list)
    last_user_reply = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    channel = Column(String(32), nullable=False)
    purpose = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    body = Column(Text, nullable=False)
    required_variables = Column(JSON, nullable=False, default=list)
    provider_template_name = Column(String(255), nullable=True)
    approved_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_message_templates_org_name"),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    contact_id = Column(BigInteger, ForeignKey("contacts.id"), nullable=True)
    purpose = Column(String(64), nullable=False)
    preferred_channel = Column(String(32), nullable=False)
    fallback_channel = Column(String(32), nullable=True)
    opt_out = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(Integer, nullable=True)
    quiet_hours_end = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "contact_id",
            "purpose",
            name="uq_notification_preferences_target_purpose",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL AND contact_id IS NULL) OR "
            "(user_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_notification_preferences_exactly_one_target",
        ),
        CheckConstraint(
            "(quiet_hours_start IS NULL OR (quiet_hours_start >= 0 AND quiet_hours_start <= 23)) "
            "AND (quiet_hours_end IS NULL OR (quiet_hours_end >= 0 AND quiet_hours_end <= 23))",
            name="ck_notification_preferences_quiet_hours_range",
        ),
    )
