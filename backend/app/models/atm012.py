from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base


class AgentDefinition(Base):
    __tablename__ = "agent_definitions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "key",
            name="uq_agent_definitions_org_key",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=True)
    key = Column(String(100), nullable=False)  # stable machine name
    name = Column(String(255), nullable=False)  # human display name
    domain = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    tool_policy = Column(JSON, nullable=False, default=dict)
    guardrail_policy = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="active")
    is_enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class AgentInvocation(Base):
    __tablename__ = "agent_invocations"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    actor_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    agent = Column(String(100), nullable=False)
    domain = Column(String(64), nullable=False)
    intent = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    input_summary = Column(Text, nullable=False)
    output_summary = Column(Text, nullable=False)
    guardrail_result = Column(String(64), nullable=False)
    tool_calls = Column(JSON, nullable=False, default=list)
    token_usage = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
