"""RBAC permission resolution service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import ALL_PERMISSIONS, PLATFORM_ROLE_NAMES
from app.models.rbac import Permission, Role, RolePermission
from app.seeds.rbac_seed import ROLE_DEFINITIONS


class RBACService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_permissions_for_role(self, role_name: str | None) -> frozenset[str]:
        normalized = (role_name or "tenant_user").strip().lower()
        if normalized in PLATFORM_ROLE_NAMES:
            return frozenset(ALL_PERMISSIONS)

        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == normalized)
        )
        role = result.scalar_one_or_none()
        if role is not None and role.permissions:
            return frozenset(p.code for p in role.permissions)

        # Fallback when RBAC tables are not seeded yet
        fallback = ROLE_DEFINITIONS.get(normalized)
        if fallback is not None:
            return fallback[1]
        return frozenset(ROLE_DEFINITIONS["tenant_user"][1])

    async def user_has_permission(self, role_name: str | None, permission: str) -> bool:
        permissions = await self.get_permissions_for_role(role_name)
        return permission in permissions

    async def list_roles(self) -> list[Role]:
        result = await self.session.execute(select(Role).order_by(Role.name))
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).order_by(Permission.module, Permission.permission)
        )
        return list(result.scalars().all())
