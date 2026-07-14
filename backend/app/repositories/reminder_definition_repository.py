"""Repository for org-scoped general reminder definitions."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_definition import ReminderDefinition


class ReminderDefinitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, row: ReminderDefinition) -> ReminderDefinition:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id(
        self,
        *,
        organization_id: int,
        definition_id: uuid.UUID,
    ) -> ReminderDefinition | None:
        result = await self.session.execute(
            select(ReminderDefinition).where(
                ReminderDefinition.id == definition_id,
                ReminderDefinition.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    def _list_filters(
        self,
        *,
        organization_id: int,
        module_key: str | None = None,
        is_active: bool | None = None,
        trigger_type: str | None = None,
        q: str | None = None,
    ) -> list:
        filters = [ReminderDefinition.organization_id == organization_id]
        if module_key:
            filters.append(ReminderDefinition.module_key == module_key.strip())
        if is_active is not None:
            filters.append(ReminderDefinition.is_active.is_(is_active))
        if trigger_type:
            filters.append(ReminderDefinition.trigger_type == trigger_type.strip().lower())
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    ReminderDefinition.reminder_name.ilike(pattern),
                    ReminderDefinition.description.ilike(pattern),
                    ReminderDefinition.module_key.ilike(pattern),
                    ReminderDefinition.trigger_key.ilike(pattern),
                )
            )
        return filters

    def _list_stmt(
        self,
        *,
        organization_id: int,
        module_key: str | None = None,
        is_active: bool | None = None,
        trigger_type: str | None = None,
        q: str | None = None,
    ) -> Select[tuple[ReminderDefinition]]:
        return (
            select(ReminderDefinition)
            .where(
                *self._list_filters(
                    organization_id=organization_id,
                    module_key=module_key,
                    is_active=is_active,
                    trigger_type=trigger_type,
                    q=q,
                )
            )
            .order_by(ReminderDefinition.created_at.desc())
        )

    async def list(
        self,
        *,
        organization_id: int,
        module_key: str | None = None,
        is_active: bool | None = None,
        trigger_type: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReminderDefinition]:
        stmt = (
            self._list_stmt(
                organization_id=organization_id,
                module_key=module_key,
                is_active=is_active,
                trigger_type=trigger_type,
                q=q,
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        organization_id: int,
        module_key: str | None = None,
        is_active: bool | None = None,
        trigger_type: str | None = None,
        q: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(ReminderDefinition).where(
            *self._list_filters(
                organization_id=organization_id,
                module_key=module_key,
                is_active=is_active,
                trigger_type=trigger_type,
                q=q,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete(self, row: ReminderDefinition) -> None:
        await self.session.delete(row)
        await self.session.flush()
