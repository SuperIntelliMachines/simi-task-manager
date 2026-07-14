from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.core import Organization
from app.services.message_template_service import MessageTemplateService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org A {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


@pytest.mark.asyncio
async def test_template_crud_and_lifecycle(async_session):
    org = await seed_org(async_session)
    service = MessageTemplateService(async_session)

    template = await service.create_template(
        organization_id=org.id,
        name="insurance_renewal",
        channel="whatsapp",
        purpose="renewal",
        body="Hi {name}, policy {policy_number} expires soon.",
        required_variables=["name", "policy_number"],
        provider_template_name="insurance_renewal_v1",
    )

    assert template.status == "draft"

    approved = await service.approve_template(template.id, approver_user_id=None)
    assert approved.status == "approved"

    archived = await service.archive_template(template.id)
    assert archived.status == "archived"


@pytest.mark.asyncio
async def test_whatsapp_template_render_fails_on_missing_variable(async_session):
    org = await seed_org(async_session)
    service = MessageTemplateService(async_session)

    template = await service.create_template(
        organization_id=org.id,
        name="insurance_renewal",
        channel="whatsapp",
        purpose="renewal",
        body="Hi {name}, policy {policy_number} expires soon.",
        required_variables=["name", "policy_number"],
    )

    with pytest.raises(ValueError):
        service.render_preview(template, {"name": "John"})
