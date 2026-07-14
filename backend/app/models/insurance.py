from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.verticals import InsurancePolicy, InsuranceLead


class PolicyStatus(PyEnum):
    ACTIVE = "ACTIVE"
    GRACE_PERIOD = "GRACE_PERIOD"
    LAPSED = "LAPSED"


class FollowUpStatus(PyEnum):
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    FOLLOW_UP_LATER = "FOLLOW_UP_LATER"


class PolicyCustomReminder(Base):
    """DEPRECATED: legacy storage for personalized offsets; new policies use reminder_configs."""

    __tablename__ = "policy_custom_reminders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    policy_id = Column(
        BigInteger,
        ForeignKey("insurance_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    reminder_unit = Column(String(20), nullable=False)
    reminder_value = Column(Integer, nullable=False)
    dnd_start_time = Column(Time, nullable=True)
    dnd_end_time = Column(Time, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    insurance_policy = relationship("InsurancePolicy", back_populates="custom_reminders")


class PolicyReminder(Base):
    """DEPRECATED: legacy scheduled sends; new schedules use reminder_instances."""

    __tablename__ = "policy_reminders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    policy_id = Column(BigInteger, ForeignKey("insurance_policies.id"), nullable=False)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    reminder_at = Column(DateTime, nullable=False)
    stage = Column(Integer, nullable=False)
    stage_direction = Column(String(20), nullable=True)
    stage_unit = Column(String(20), nullable=True)
    stage_value = Column(Integer, nullable=True)
    reminder_type = Column(String(32), nullable=True)
    channel = Column(String(50), nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="scheduled")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    policy = relationship(InsurancePolicy, backref="reminders")
    follow_ups = relationship(InsuranceLead, secondary="reminder_followup_link", backref="reminders")


class ReminderFollowupLink(Base):
    __tablename__ = "reminder_followup_link"

    reminder_id = Column(BigInteger, ForeignKey("policy_reminders.id"), primary_key=True)
    followup_id = Column(BigInteger, ForeignKey("insurance_leads.id"), primary_key=True)


# Backwards compatibility: other modules may import `Policy` / `FollowUp` from
# `app.models.insurance`. Alias them to the legacy verticals models so code
# continues to work while we migrate services/schemas in Step 2.
Policy = InsurancePolicy
FollowUp = InsuranceLead
