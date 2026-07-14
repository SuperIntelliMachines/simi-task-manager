from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base


class ChannelConnection(Base):
    __tablename__ = "channel_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", "channel", name="uq_channel_connections_org_channel"),
    )

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    channel = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    provider_reference = Column(String(255), nullable=True)
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ContactChannelIdentity(Base):
    __tablename__ = "contact_channel_identities"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "channel",
            "external_user_id",
            name="uq_contact_channel_identity_external_user",
        ),
        UniqueConstraint(
            "organization_id",
            "channel",
            "contact_id",
            name="uq_contact_channel_identity_contact_channel",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    contact_id = Column(BigInteger, ForeignKey("contacts.id"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    channel = Column(String(32), nullable=False)
    external_user_id = Column(String(255), nullable=False)
    external_chat_id = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    is_opted_out = Column(Boolean, nullable=False, default=False)
    last_inbound_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class InboundMessage(Base):
    __tablename__ = "inbound_messages"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "external_message_id",
            name="uq_inbound_messages_channel_external_message",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    channel_connection_id = Column(BigInteger, ForeignKey("channel_connections.id"), nullable=True)
    identity_id = Column(BigInteger, ForeignKey("contact_channel_identities.id"), nullable=True)
    channel = Column(String(32), nullable=False)
    external_message_id = Column(String(255), nullable=False)
    external_user_id = Column(String(255), nullable=False)
    external_chat_id = Column(String(255), nullable=True)
    message_type = Column(String(64), nullable=False, default="text")
    text = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
