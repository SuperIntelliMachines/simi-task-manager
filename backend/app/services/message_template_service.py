from datetime import UTC, datetime
from string import Formatter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import MessageTemplate


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def extract_template_variables(body: str) -> set[str]:
    vars_found: set[str] = set()
    for _, field_name, _, _ in Formatter().parse(body):
        if field_name:
            vars_found.add(field_name)
    return vars_found


class MessageTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_templates(self, organization_id: int) -> list[MessageTemplate]:
        result = await self.session.execute(
            select(MessageTemplate)
            .where(MessageTemplate.organization_id == organization_id)
            .order_by(MessageTemplate.created_at.desc())
        )
        return list(result.scalars())

    async def create_template(
        self,
        *,
        organization_id: int,
        name: str,
        channel: str,
        purpose: str,
        body: str,
        required_variables: list[str],
        provider_template_name: str | None = None,
    ) -> MessageTemplate:
        self._validate_required_variables(body, required_variables)
        now = utcnow_naive()
        item = MessageTemplate(
            organization_id=organization_id,
            name=name,
            channel=channel,
            purpose=purpose,
            status="draft",
            body=body,
            required_variables=required_variables,
            provider_template_name=provider_template_name,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update_template(self, template_id: int, updates: dict) -> MessageTemplate:
        item = await self.session.get(MessageTemplate, template_id)
        if item is None:
            raise ValueError("template not found")

        next_body = updates.get("body", item.body)
        next_required = updates.get("required_variables", item.required_variables)
        self._validate_required_variables(next_body, next_required)

        for key, value in updates.items():
            setattr(item, key, value)

        item.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def approve_template(self, template_id: int, approver_user_id: int | None) -> MessageTemplate:
        item = await self.session.get(MessageTemplate, template_id)
        if item is None:
            raise ValueError("template not found")

        item.status = "approved"
        item.approved_by_user_id = approver_user_id
        item.approved_at = utcnow_naive()
        item.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def archive_template(self, template_id: int) -> MessageTemplate:
        item = await self.session.get(MessageTemplate, template_id)
        if item is None:
            raise ValueError("template not found")

        item.status = "archived"
        item.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(item)
        return item

    def render_preview(self, template: MessageTemplate, sample_data: dict[str, str]) -> str:
        required = set(template.required_variables or [])
        missing = [var for var in required if var not in sample_data]
        if missing:
            raise ValueError(f"missing required variable(s): {', '.join(sorted(missing))}")

        try:
            return template.body.format(**sample_data)
        except KeyError as exc:
            raise ValueError(f"missing variable: {exc.args[0]}") from exc

    def map_whatsapp_provider_template_name(self, template: MessageTemplate) -> str:
        return template.provider_template_name or template.name

    def _validate_required_variables(self, body: str, required_variables: list[str]) -> None:
        found = extract_template_variables(body)
        missing = [var for var in required_variables if var not in found]
        if missing:
            raise ValueError(f"required variable(s) not found in body: {', '.join(missing)}")
