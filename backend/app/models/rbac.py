"""RBAC models: roles, permissions, and role-permission mappings."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False)

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("module", "permission", name="uq_permissions_module_permission"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(64), nullable=False)
    permission = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)

    @property
    def code(self) -> str:
        return f"{self.module}:{self.permission}"

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),)

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
