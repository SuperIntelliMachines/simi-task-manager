from sqlalchemy import (
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
from sqlalchemy.orm import relationship
from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    support_access_sessions = relationship(
        "SupportAccessSession",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), nullable=False, default="tenant_user")
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(64), nullable=False, default="general")
    status = Column(String(50), nullable=False)
    due_at = Column(DateTime, nullable=True)
    priority = Column(String(16), nullable=False, default="medium")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND contact_id IS NULL) OR "
            "(user_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_task_assignments_exactly_one_recipient",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    contact_id = Column(BigInteger, ForeignKey("contacts.id"), nullable=True)
    status = Column(String(32), nullable=False, default="assigned")
    assigned_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("organization_id", "dedupe_key", name="uq_reminders_org_dedupe_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=False)
    dedupe_key = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ReminderAttempt(Base):
    __tablename__ = "reminder_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    reminder_id = Column(BigInteger, ForeignKey("reminders.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False)
    error_message = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    definition = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    workflow_template_id = Column(BigInteger, ForeignKey("workflow_templates.id"), nullable=False)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=True)
    status = Column(String(32), nullable=False, default="running")
    current_step = Column(String(255), nullable=True)
    state_payload = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


# Add other models here following the same pattern.