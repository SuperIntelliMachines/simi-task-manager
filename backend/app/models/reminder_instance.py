from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReminderInstance(Base):
    __tablename__ = "reminder_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer,
        ForeignKey("reminder_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    sent_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    config = relationship("ReminderConfig", back_populates="instances")
