from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.column_types import TextArray


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    policyholder_id = Column(BigInteger, ForeignKey("contacts.id"), nullable=False)
    policy_number = Column(String(50), nullable=False, unique=True)
    premium = Column(BigInteger, nullable=False)
    policy_type = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    renewal_frequency = Column(String(32), nullable=False, server_default="yearly")
    assigned_agent_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    preferred_channel = Column(TextArray, nullable=True)
    reminder_type = Column(String(32), nullable=False, server_default="default")
    reminder_unit = Column(String(16), nullable=True)
    reminder_value = Column(Integer, nullable=True)
    dnd_start_time = Column(Time, nullable=True)
    dnd_end_time = Column(Time, nullable=True)
    mobile_number = Column(String(20), nullable=True)
    telegram_chat_id = Column(BigInteger, nullable=True)
    telegram_username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    document_name = Column(String(255), nullable=True)
    document_path = Column(Text, nullable=True)
    expiry_date = Column(DateTime, nullable=False)
    grace_period_days = Column(Integer, nullable=False, server_default="30")
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    custom_reminders = relationship(
        "PolicyCustomReminder",
        back_populates="insurance_policy",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class InsuranceLead(Base):
    __tablename__ = "insurance_leads"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    contact_id = Column(BigInteger, ForeignKey("contacts.id"), nullable=False)
    assigned_agent_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    source = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    demo_logged_at = Column(DateTime, nullable=True)
    followup_due_at = Column(DateTime, nullable=True)
    related_policy_id = Column(BigInteger, ForeignKey("insurance_policies.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ConstructionProject(Base):
    __tablename__ = "construction_projects"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


# Add other vertical-specific models here.