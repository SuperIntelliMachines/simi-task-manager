"""Seed default RBAC roles and permissions."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ALL_PERMISSIONS, PLATFORM_ROLE_NAMES
from app.models.rbac import Permission, Role, RolePermission

ROLE_DEFINITIONS: dict[str, tuple[str, frozenset[str]]] = {
    "platform_admin": (
        "Platform Admin",
        frozenset(ALL_PERMISSIONS),
    ),
    "support_engineer": (
        "Support Engineer",
        frozenset(ALL_PERMISSIONS),
    ),
    "implementation_manager": (
        "Implementation Manager",
        frozenset(ALL_PERMISSIONS),
    ),
    "org_admin": (
        "Organization Admin",
        frozenset(
            p for p in ALL_PERMISSIONS if not p.startswith("admin:")
        ),
    ),
    "manager": (
        "Manager",
        frozenset(
            {
                "insurance:view",
                "insurance:create",
                "insurance:update",
                "claims:view",
                "claims:create",
                "claims:update",
                "claims:assign",
                "reminders:view",
                "reminders:create",
                "reminders:update",
                "reminders:process",
                "leads:view",
                "leads:create",
                "leads:update",
                "bms:view",
                "bms:create",
                "bms:update",
                "bms:assign",
                "agents:view",
                "agents:invoke",
                "users:view",
                "users:invite",
                "tasks:view",
                "tasks:create",
                "tasks:update",
                "tasks:complete",
                "channels:view",
                "channels:create",
                "channels:update",
                "channels:test",
                "templates:view",
                "templates:create",
                "templates:update",
                "approvals:view",
                "approvals:approve",
                "approvals:reject",
            }
        ),
    ),
    "agent": (
        "Agent",
        frozenset(
            {
                "insurance:view",
                "insurance:create",
                "insurance:update",
                "claims:view",
                "claims:create",
                "claims:update",
                "reminders:view",
                "reminders:create",
                "leads:view",
                "leads:create",
                "leads:update",
                "bms:view",
                "bms:create",
                "agents:view",
                "agents:invoke",
                "tasks:view",
                "tasks:create",
                "tasks:update",
                "tasks:complete",
                "channels:view",
                "templates:view",
                "approvals:view",
            }
        ),
    ),
    "viewer": (
        "Viewer",
        frozenset(
            {
                "insurance:view",
                "claims:view",
                "reminders:view",
                "leads:view",
                "bms:view",
                "agents:view",
                "users:view",
                "tasks:view",
                "channels:view",
                "templates:view",
                "approvals:view",
            }
        ),
    ),
    # Backward compatibility for existing users.role value
    "tenant_user": (
        "Tenant User",
        frozenset(
            {
                "insurance:view",
                "insurance:create",
                "insurance:update",
                "reminders:view",
                "reminders:create",
                "reminders:update",
                "leads:view",
                "leads:create",
                "leads:update",
                "tasks:view",
                "tasks:create",
                "tasks:update",
                "tasks:complete",
                "channels:view",
                "templates:view",
                "approvals:view",
                "agents:view",
                "agents:invoke",
            }
        ),
    ),
}


def _split_permission(code: str) -> tuple[str, str]:
    module, action = code.split(":", 1)
    return module, action


async def seed_rbac(session: AsyncSession) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = await session.execute(select(Role.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    permission_rows: dict[str, Permission] = {}
    for code in ALL_PERMISSIONS:
        module, action = _split_permission(code)
        perm = Permission(module=module, permission=action, description=code)
        session.add(perm)
        await session.flush()
        permission_rows[code] = perm

    for role_name, (description, perm_codes) in ROLE_DEFINITIONS.items():
        role = Role(
            name=role_name,
            description=description,
            is_system=True,
            created_at=now,
        )
        session.add(role)
        await session.flush()
        for code in perm_codes:
            perm = permission_rows.get(code)
            if perm is None:
                continue
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        await session.flush()

    await session.commit()


def is_platform_role(role_name: str | None) -> bool:
    return (role_name or "") in PLATFORM_ROLE_NAMES
