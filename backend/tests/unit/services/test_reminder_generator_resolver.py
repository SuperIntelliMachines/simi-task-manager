from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact, Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_resolvers import PolicyReminderResolver, ReminderResolverFactory
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_policy_resolver_lists_policies_and_anchor_date(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=15000)

    org = Organization(name=f"Resolver Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15001,
        organization_id=org.id,
        name="Resolver Holder",
        phone="+919666666666",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = now + timedelta(days=20)
    policy = InsurancePolicy(
        id=15002,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"RES-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919666666666",
        preferred_channel=["whatsapp"],
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    resolver = PolicyReminderResolver()
    entities = await resolver.list_entities(async_session, org.id)
    assert len(entities) == 1
    assert entities[0].entity_id == policy.id
    assert entities[0].anchor_date == expiry.replace(tzinfo=None)
    assert entities[0].recipient == "+919666666666"
    assert entities[0].reference_id == policy.policy_number
    assert entities[0].customer_name == "Resolver Holder"

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
        template_key="policy_renewal_reminder",
        offset_value=30,
        offset_unit="days",
        is_active=True,
    )
    assert resolver.is_eligible(entities[0], configs=[config]) is True


@pytest.mark.asyncio
async def test_policy_resolver_build_template_context(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=15200)

    org = Organization(name=f"Ctx Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15201,
        organization_id=org.id,
        name="Template Holder",
        phone="+919444444444",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=15202,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="CTX-001",
        premium=1000,
        policy_type="health",
        mobile_number="+919444444444",
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    resolver = PolicyReminderResolver()
    entity = await resolver.get_entity(async_session, org.id, policy.id)
    assert entity is not None

    scheduled_at = datetime(2026, 7, 4, 15, 30, 0)
    context = resolver.build_template_context(
        entity,
        entity_label="Health Renewal",
        sender_name="ABC Insurance",
        scheduled_at=scheduled_at,
    )
    assert context == {
        "customer_name": "Template Holder",
        "entity_label": "Health Renewal",
        "reminder_date": "04-07-2026 03:30 PM",
        "sender_name": "ABC Insurance",
    }
    assert resolver.get_default_entity_label() == "Policy Renewal"
    assert resolver.get_whatsapp_template_spec() == ("policy_renewal_reminder", "en_US")


@pytest.mark.asyncio
async def test_generate_from_active_configs_discovers_policy_entities(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=15100)

    org = Organization(name=f"Gen Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15101,
        organization_id=org.id,
        name="Gen Holder",
        phone="+919555555555",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = datetime(2026, 8, 8, 0, 0, 0)
    policy = InsurancePolicy(
        id=15102,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"GEN-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919555555555",
        preferred_channel=["whatsapp"],
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="policy",
            entity_id=policy.id,
            channel="whatsapp",
            template_key="policy_renewal_reminder",
            offset_value=7,
            offset_unit="days",
            is_active=True,
        )
    )
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    service = ReminderGeneratorService(async_session, resolver_factory=factory)
    created = await service.generate_from_active_configs(organization_id=org.id)

    assert len(created) == 1
    assert created[0].scheduled_at == datetime(2026, 8, 1, 9, 0, 0)
    assert created[0].entity_id == policy.id

    second = await service.generate_from_active_configs(organization_id=org.id)
    assert second == []


@pytest.mark.asyncio
async def test_generate_from_active_configs_skips_unknown_entity_type(async_session):
    org = Organization(name=f"Unknown Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="pest_control",
            entity_id=1,
            channel="whatsapp",
            template_key="generic_reminder",
            offset_value=3,
            offset_unit="days",
            is_active=True,
        )
    )
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    service = ReminderGeneratorService(async_session, resolver_factory=factory)
    created = await service.generate_from_active_configs(organization_id=org.id)
    assert created == []

    rows = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(
                    ReminderInstance.organization_id == org.id,
                    ReminderInstance.entity_type == "pest_control",
                )
            )
        ).scalars()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_policy_resolver_maps_expiry_and_renewal_keys(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=15300)

    org = Organization(name=f"Anchor Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15301,
        organization_id=org.id,
        name="Anchor Holder",
        phone="+919111111111",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = datetime(2026, 9, 30, 0, 0, 0)
    policy = InsurancePolicy(
        id=15302,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"ANC-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919111111111",
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    resolver = PolicyReminderResolver()
    entity = await resolver.get_entity(async_session, org.id, policy.id)
    assert entity is not None
    assert resolver.resolve_anchor(entity, "date", "expiry_date") == expiry
    assert resolver.resolve_anchor(entity, "date", "renewal_date") == expiry
    assert resolver.resolve_anchor(entity, "date", "anchor_date") == expiry


@pytest.mark.asyncio
async def test_generate_insurance_before_expiry_and_renewal(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=15400)

    org = Organization(name=f"Ins Gen {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15401,
        organization_id=org.id,
        name="Ins Holder",
        phone="+919222222222",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = datetime(2026, 8, 10, 0, 0, 0)
    policy = InsurancePolicy(
        id=15402,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"INS-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919222222222",
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add_all(
        [
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=policy.id,
                channel="whatsapp",
                offset_value=30,
                offset_unit="days",
                is_active=True,
                anchor_type="date",
                anchor_key="expiry_date",
                offset_direction="before",
            ),
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=policy.id,
                channel="email",
                offset_value=15,
                offset_unit="days",
                is_active=True,
                anchor_type="date",
                anchor_key="renewal_date",
                offset_direction="before",
            ),
        ]
    )
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    service = ReminderGeneratorService(async_session, resolver_factory=factory)
    created = await service.generate_from_active_configs(organization_id=org.id)

    scheduled = sorted(item.scheduled_at for item in created)
    assert scheduled == [
        datetime(2026, 7, 11, 9, 0, 0),  # 30 days before
        datetime(2026, 7, 26, 9, 0, 0),  # 15 days before
    ]


@pytest.mark.asyncio
async def test_generate_claims_workflow_after_anchors(async_session):
    from app.services.reminder_resolvers.base import ReminderEntitySnapshot
    from app.services.reminder_resolvers.claims_resolver import ClaimsReminderResolver

    org = Organization(name=f"Claims Gen {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    case = {
        "id": 7701,
        "case_id": 7701,
        "status": "pending_submission",
        "customer_name": "Claims User",
        "customer_phone": "+919333333333",
        "pending_submission_at": "2026-07-10T08:00:00+00:00",
        "return_pending_at": "2026-07-11T12:00:00+00:00",
    }

    class StubClaimsResolver(ClaimsReminderResolver):
        async def list_entities(self, session, organization_id):
            return [
                ReminderEntitySnapshot(
                    organization_id=organization_id,
                    entity_type="claims",
                    entity_id=7701,
                    anchor_date=None,
                    recipient="+919333333333",
                    reference_id="7701",
                    customer_name="Claims User",
                    source=case,
                )
            ]

        async def get_entity(self, session, organization_id, entity_id):
            entities = await self.list_entities(session, organization_id)
            return next((e for e in entities if e.entity_id == entity_id), None)

    async_session.add_all(
        [
            ReminderConfig(
                organization_id=org.id,
                entity_type="claims",
                entity_id=7701,
                channel="email",
                offset_value=24,
                offset_unit="hours",
                is_active=True,
                anchor_type="workflow",
                anchor_key="pending_submission",
                offset_direction="after",
            ),
            ReminderConfig(
                organization_id=org.id,
                entity_type="claims",
                entity_id=7701,
                channel="whatsapp",
                offset_value=48,
                offset_unit="hours",
                is_active=True,
                anchor_type="workflow",
                anchor_key="return_pending",
                offset_direction="after",
            ),
        ]
    )
    await async_session.commit()

    factory = ReminderResolverFactory({"claims": StubClaimsResolver()})
    service = ReminderGeneratorService(async_session, resolver_factory=factory)
    created = await service.generate_from_active_configs(organization_id=org.id)

    scheduled = sorted(item.scheduled_at for item in created)
    assert scheduled == [
        datetime(2026, 7, 11, 8, 0, 0),   # 24h after pending_submission
        datetime(2026, 7, 13, 12, 0, 0),  # 48h after return_pending
    ]


@pytest.mark.asyncio
async def test_generate_mixed_default_and_explicit_anchors(async_session):
    """Legacy configs (defaults) and explicit expiry configs both schedule correctly."""
    patch_sqlite_session_bigint_ids(async_session, start_id=15500)

    org = Organization(name=f"Mixed Gen {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=15501,
        organization_id=org.id,
        name="Mixed Holder",
        phone="+919444444444",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = datetime(2026, 8, 8, 0, 0, 0)
    policy = InsurancePolicy(
        id=15502,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"MIX-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="motor",
        mobile_number="+919444444444",
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add_all(
        [
            # Legacy-style defaults (anchor_date / before) — DB server defaults apply if omitted;
            # set explicitly for SQLite insert clarity.
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=policy.id,
                channel="whatsapp",
                offset_value=7,
                offset_unit="days",
                is_active=True,
                anchor_type="date",
                anchor_key="anchor_date",
                offset_direction="before",
            ),
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=policy.id,
                channel="email",
                offset_value=1,
                offset_unit="days",
                is_active=True,
                anchor_type="date",
                anchor_key="expiry_date",
                offset_direction="before",
            ),
        ]
    )
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    service = ReminderGeneratorService(async_session, resolver_factory=factory)
    created = await service.generate_from_active_configs(organization_id=org.id)

    scheduled = sorted(item.scheduled_at for item in created)
    assert scheduled == [
        datetime(2026, 8, 1, 9, 0, 0),
        datetime(2026, 8, 7, 9, 0, 0),
    ]
