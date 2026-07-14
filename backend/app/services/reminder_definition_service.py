"""Service for General Reminder Definition CRUD (definitions only).

Does not generate instances, resolve recipients, or send notifications.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_definition import ReminderDefinition
from app.repositories.reminder_definition_repository import ReminderDefinitionRepository
from app.schemas.general_reminder import (
    GeneralReminderCreateRequest,
    GeneralReminderUpdateRequest,
)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ReminderDefinitionService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ReminderDefinitionRepository | None = None,
    ):
        self.session = session
        self.repository = repository or ReminderDefinitionRepository(session)

    async def create(
        self,
        *,
        organization_id: int,
        created_by: int | None,
        payload: GeneralReminderCreateRequest,
    ) -> ReminderDefinition:
        now = utcnow_naive()
        row = ReminderDefinition(
            organization_id=int(organization_id),
            module_key=payload.module_key,
            reminder_name=payload.reminder_name,
            description=payload.description,
            trigger_type=payload.trigger.type,
            trigger_key=payload.trigger.key,
            offset_value=payload.schedule.offset_value,
            offset_unit=payload.schedule.offset_unit,
            offset_direction=payload.schedule.direction,
            recipient_type=payload.recipient.type,
            recipient_value=list(payload.recipient.value),
            channels=list(payload.channels),
            template_key=payload.template_key,
            is_active=payload.is_active,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        return await self.repository.create(row)

    async def get(
        self,
        *,
        organization_id: int,
        definition_id: uuid.UUID,
    ) -> ReminderDefinition:
        row = await self.repository.get_by_id(
            organization_id=organization_id,
            definition_id=definition_id,
        )
        if row is None:
            raise ValueError("Reminder definition not found")
        return row

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
    ) -> tuple[list[ReminderDefinition], int]:
        items = await self.repository.list(
            organization_id=organization_id,
            module_key=module_key,
            is_active=is_active,
            trigger_type=trigger_type,
            q=q,
            limit=limit,
            offset=offset,
        )
        total = await self.repository.count(
            organization_id=organization_id,
            module_key=module_key,
            is_active=is_active,
            trigger_type=trigger_type,
            q=q,
        )
        return items, total

    async def update(
        self,
        *,
        organization_id: int,
        definition_id: uuid.UUID,
        payload: GeneralReminderUpdateRequest,
    ) -> ReminderDefinition:
        row = await self.get(organization_id=organization_id, definition_id=definition_id)
        data = payload.model_dump(exclude_unset=True)

        if "module_key" in data:
            row.module_key = data["module_key"]
        if "reminder_name" in data:
            row.reminder_name = data["reminder_name"]
        if "description" in data:
            row.description = data["description"]
        if "trigger" in data and data["trigger"] is not None:
            row.trigger_type = data["trigger"]["type"]
            row.trigger_key = data["trigger"]["key"]
        if "schedule" in data and data["schedule"] is not None:
            row.offset_value = data["schedule"]["offset_value"]
            row.offset_unit = data["schedule"]["offset_unit"]
            row.offset_direction = data["schedule"]["direction"]
        if "recipient" in data and data["recipient"] is not None:
            row.recipient_type = data["recipient"]["type"]
            row.recipient_value = list(data["recipient"]["value"])
        if "channels" in data and data["channels"] is not None:
            row.channels = list(data["channels"])
        if "template_key" in data:
            row.template_key = data["template_key"]
        if "is_active" in data and data["is_active"] is not None:
            row.is_active = data["is_active"]

        row.updated_at = utcnow_naive()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def delete(
        self,
        *,
        organization_id: int,
        definition_id: uuid.UUID,
    ) -> None:
        row = await self.get(organization_id=organization_id, definition_id=definition_id)
        await self.repository.delete(row)
