from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class SupportAccessSession(Base):
    __tablename__ = "support_access_sessions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    reason = Column(String, nullable=False)
    expiry = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    organization = relationship("Organization", back_populates="support_access_sessions")
    created_by_user = relationship("User")