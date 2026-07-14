import pytest
from sqlalchemy import select
from uuid import uuid4

from app.core.database import AsyncSessionLocal
from app.models.atm005 import ContactChannelIdentity, InboundMessage
from app.models.core import Organization


@pytest.mark.asyncio
async def test_channel_webhooks(async_client):
    org_id = 1

    async with AsyncSessionLocal() as session:
        existing = await session.get(Organization, org_id)
        if existing is None:
            from datetime import UTC, datetime

            now = datetime.now(UTC).replace(tzinfo=None)
            session.add(Organization(id=org_id, name=f"Org A {uuid4().hex[:8]}", created_at=now, updated_at=now))
            await session.commit()

    tg_payload = {
        "update_id": 1001,
        "message": {
            "message_id": 10,
            "text": "hello",
            "from": {"id": 1234},
            "chat": {"id": 5678},
        },
    }

    tg_response = await async_client.post(
        "/api/v1/telegram/webhook",
        json={"organization_id": org_id, "payload": tg_payload},
    )
    assert tg_response.status_code == 200

    async with AsyncSessionLocal() as session:
        inbound_rows = await session.execute(
            select(InboundMessage).where(InboundMessage.channel == "telegram")
        )
        assert len(list(inbound_rows.scalars())) >= 1

    verify_response = await async_client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "",
            "hub.challenge": "123",
        },
    )
    assert verify_response.status_code == 200

    wa_stop_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"id": "wamid-1", "from": "91999", "type": "text", "text": {"body": "STOP"}}],
                            "contacts": [{"wa_id": "91999"}],
                        }
                    }
                ]
            }
        ]
    }

    wa_response = await async_client.post(
        "/api/v1/whatsapp/webhook",
        json={"organization_id": org_id, "payload": wa_stop_payload},
    )
    assert wa_response.status_code == 200

    async with AsyncSessionLocal() as session:
        identities = await session.execute(
            select(ContactChannelIdentity).where(
                ContactChannelIdentity.channel == "whatsapp",
                ContactChannelIdentity.external_user_id == "91999",
            )
        )
        row = identities.scalar_one_or_none()
        assert row is not None
        assert row.is_opted_out is True
