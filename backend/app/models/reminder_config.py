from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
    true,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    DEFAULT_REMINDER_STOP_CONDITION,
    ReminderAnchorType,
    ReminderOffsetDirection,
    ReminderStopCondition,
)


class ReminderConfig(Base):
    """Generic reminder rule for any module entity.

    Scheduling is described by:
    - anchor_type / anchor_key: which entity clock to use (date field or workflow stage)
    - offset_value / offset_unit / offset_direction: when to fire relative to that clock
    - absolute_scheduled_at: optional fixed send time (overrides relative scheduling)
    """

    __tablename__ = "reminder_configs"
    __table_args__ = (
        CheckConstraint(
            f"anchor_type IN ('{ReminderAnchorType.DATE.value}', '{ReminderAnchorType.WORKFLOW.value}')",
            name="ck_reminder_configs_anchor_type",
        ),
        CheckConstraint(
            f"offset_direction IN ('{ReminderOffsetDirection.BEFORE.value}', '{ReminderOffsetDirection.AFTER.value}')",
            name="ck_reminder_configs_offset_direction",
        ),
        CheckConstraint(
            # trim() is portable across PostgreSQL and SQLite (tests use SQLite).
            "length(trim(anchor_key)) > 0",
            name="ck_reminder_configs_anchor_key_nonempty",
        ),
        CheckConstraint(
            f"stop_condition IN ('{ReminderStopCondition.NEVER.value}', "
            f"'{ReminderStopCondition.ENTITY_INELIGIBLE.value}', "
            f"'{ReminderStopCondition.WORKFLOW_STATUS_CHANGED.value}', "
            f"'{ReminderStopCondition.END_DATE_REACHED.value}', "
            f"'{ReminderStopCondition.MAX_ATTEMPTS_REACHED.value}')",
            name="ck_reminder_configs_stop_condition",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    channel = Column(String(50), nullable=False)
    template_key = Column(String(100), nullable=True)
    entity_label = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    # Module-specific WhatsApp/template placeholder values (any JSON object).
    template_variables = Column(JSON, nullable=False, default=dict, server_default="{}")
    # Module-specific recipient contact details (any JSON object).
    recipient_data = Column(JSON, nullable=False, default=dict, server_default="{}")

    # Anchor selection (generic — module-specific keys live in anchor_key values, not columns)
    anchor_type = Column(
        String(20),
        nullable=False,
        default=ReminderAnchorType.DATE.value,
        server_default=ReminderAnchorType.DATE.value,
    )
    # Free-form key resolved by ReminderResolvers (e.g. "anchor_date", "expiry_date", "pending_submission").
    anchor_key = Column(
        String(100),
        nullable=False,
        default=DEFAULT_REMINDER_ANCHOR_KEY,
        server_default=DEFAULT_REMINDER_ANCHOR_KEY,
    )

    # Trigger offset relative to the resolved anchor (API alias: trigger_offset_*).
    offset_value = Column(Integer, nullable=False)
    offset_unit = Column(String(20), nullable=False, default="days")
    # BEFORE preserves historical Insurance behavior (send N units before the anchor).
    offset_direction = Column(
        String(20),
        nullable=False,
        default=ReminderOffsetDirection.BEFORE.value,
        server_default=ReminderOffsetDirection.BEFORE.value,
    )

    repeat_enabled = Column(Boolean, nullable=False, default=False, server_default="0")
    repeat_frequency_value = Column(Integer, nullable=True)
    repeat_frequency_unit = Column(String(20), nullable=True)
    max_attempts = Column(Integer, nullable=True)
    stop_condition = Column(
        String(50),
        nullable=False,
        default=DEFAULT_REMINDER_STOP_CONDITION,
        server_default=DEFAULT_REMINDER_STOP_CONDITION,
    )
    stop_condition_config = Column(JSON, nullable=True)

    time_of_day = Column(Time, nullable=True)
    absolute_scheduled_at = Column(DateTime, nullable=True)
    dnd_start = Column(Time, nullable=True)
    dnd_end = Column(Time, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    instances = relationship(
        "ReminderInstance",
        back_populates="config",
        cascade="all, delete-orphan",
    )
