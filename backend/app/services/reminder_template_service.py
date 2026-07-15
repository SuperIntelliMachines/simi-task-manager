"""Service for Reminder Template CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_template import (
    WHATSAPP_APPROVAL_DRAFT,
    ReminderTemplate,
)
from app.schemas.reminder_template import ReminderTemplateCreate, ReminderTemplateUpdate


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ReminderTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_template(
        self,
        *,
        organization_id: int,
        created_by: int | None,
        payload: ReminderTemplateCreate,
    ) -> ReminderTemplate:
        now = utcnow_naive()
        approval_status = WHATSAPP_APPROVAL_DRAFT if payload.channel == "whatsapp" else None
        row = ReminderTemplate(
            organization_id=int(organization_id),
            created_by=created_by,
            name=payload.name,
            channel=payload.channel,
            subject=payload.subject,
            title=payload.title,
            body=payload.body,
            variables=list(payload.variables),
            is_active=payload.is_active,
            whatsapp_template_name=payload.whatsapp_template_name,
            approval_status=approval_status,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_template(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID,
    ) -> ReminderTemplate:
        row = await self._get_owned(organization_id=organization_id, template_id=template_id)
        if row is None:
            raise ValueError("Reminder template not found")
        return row

    async def list_templates(
        self,
        *,
        organization_id: int,
        channel: str | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ReminderTemplate], int]:
        filters = [ReminderTemplate.organization_id == int(organization_id)]
        if channel:
            filters.append(ReminderTemplate.channel == channel.strip().lower())
        if is_active is not None:
            filters.append(ReminderTemplate.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    ReminderTemplate.name.ilike(pattern),
                    ReminderTemplate.body.ilike(pattern),
                    ReminderTemplate.subject.ilike(pattern),
                    ReminderTemplate.title.ilike(pattern),
                )
            )

        items_stmt: Select[tuple[ReminderTemplate]] = (
            select(ReminderTemplate)
            .where(*filters)
            .order_by(ReminderTemplate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())

        count_stmt = select(func.count()).select_from(ReminderTemplate).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def update_template(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID,
        payload: ReminderTemplateUpdate,
    ) -> ReminderTemplate:
        row = await self.get_template(organization_id=organization_id, template_id=template_id)
        data = payload.model_dump(exclude_unset=True)

        next_channel = data.get("channel", row.channel)
        for field in (
            "name",
            "channel",
            "subject",
            "title",
            "body",
            "is_active",
            "whatsapp_template_name",
        ):
            if field in data:
                setattr(row, field, data[field])
        if "variables" in data and data["variables"] is not None:
            row.variables = list(data["variables"])

        if row.channel == "email" and not row.subject:
            raise ValueError("subject is required for email templates")
        if row.channel == "in_app" and not row.title:
            raise ValueError("title is required for in_app templates")
        if not row.body or not str(row.body).strip():
            raise ValueError("body is required")

        if next_channel == "whatsapp":
            if row.approval_status is None:
                row.approval_status = WHATSAPP_APPROVAL_DRAFT
            if not row.whatsapp_template_name:
                row.whatsapp_template_name = row.name
        elif row.channel != "whatsapp" and "channel" in data:
            row.approval_status = None
            row.meta_template_id = None
            row.approved_at = None
            row.rejection_reason = None

        row.updated_at = utcnow_naive()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def delete_template(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID,
    ) -> None:
        row = await self.get_template(organization_id=organization_id, template_id=template_id)
        await self.session.delete(row)
        await self.session.flush()

    async def _get_owned(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID,
    ) -> ReminderTemplate | None:
        stmt = select(ReminderTemplate).where(
            ReminderTemplate.id == template_id,
            ReminderTemplate.organization_id == int(organization_id),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
