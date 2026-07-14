from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.telegram.insurance_commands import TelegramInsuranceCommandService


@pytest.mark.asyncio
async def test_dashboard_summary_uses_ui_kpis():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    mock_insurance = AsyncMock()
    mock_insurance.get_ui_dashboard_kpis = AsyncMock(
        return_value={
            "organization_id": 607,
            "total_policies": 14,
            "active_policies": 5,
            "due_renewals": 1,
            "expiring_policies": 2,
            "expired_policies": 6,
            "pending_followups": 11,
        }
    )
    service.insurance = mock_insurance

    text = await service.dashboard_summary()

    mock_insurance.get_ui_dashboard_kpis.assert_awaited_once_with(607)
    assert "Total Policies: 14" in text
    assert "Active Policies: 5" in text
    assert "Due Renewals: 1" in text
    assert "Expiring Policies: 2" in text
    assert "Expired Policies: 6" in text
    assert "Pending Follow-ups: 11" in text


@pytest.mark.asyncio
async def test_policies_summary_format():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=1)

    service._dashboard_counts = AsyncMock(
        return_value={
            "organization_id": 1,
            "total_policies": 10,
            "active_policies": 7,
            "due_renewals": 1,
            "expiring_policies": 2,
            "expired_policies": 1,
            "pending_followups": 0,
        }
    )

    text = await service.policies_summary()

    assert "Policy Overview" in text
    assert "Total Policies: 10" in text
    assert "Due Renewals: 1" in text


@pytest.mark.asyncio
async def test_create_policy_with_reminder_channel_in_response():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    policy = MagicMock()
    policy.id = 1
    policy.policy_number = "POL-100"
    service.insurance.create_policy = AsyncMock(return_value=policy)
    service.insurance.start_policy_renewal_workflow = AsyncMock(return_value={})

    text = await service.create_policy(
        customer_name="Kishan",
        policy_type="Motor",
        expiry_date=MagicMock(strftime=lambda fmt: "26-Jul-2026"),
        reminder_channel="WhatsApp",
    )

    assert "Policy Created" in text
    assert "Kishan" in text
    assert "Reminder Requested: WhatsApp" in text
    assert "Reminder scheduling will be handled separately" in text
    service.insurance.create_policy.assert_awaited_once()
    assert service.insurance.create_policy.await_args.kwargs["preferred_channel"] == ["whatsapp"]


@pytest.mark.asyncio
async def test_log_followup_success():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    lead = MagicMock()
    lead.id = 42
    service.insurance.create_lead = AsyncMock(return_value=lead)
    service.insurance.start_lead_followup_workflow = AsyncMock(return_value={})

    text = await service.log_followup(customer_name="Priya", followup_days=3)

    assert "Follow-up Logged Successfully" in text
    assert "Priya" in text
    service.insurance.create_lead.assert_awaited_once()
    service.insurance.start_lead_followup_workflow.assert_awaited_once()


@pytest.mark.asyncio
async def test_expiring_policies_within_days_formats_response():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive

    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    now = utcnow_naive()
    policy = MagicMock()
    policy.policy_number = "POL-4321"
    policy.policyholder_id = 219
    policy.expiry_date = now + timedelta(days=3)

    service.insurance.list_policies = AsyncMock(return_value=[policy])
    service._contact_name = AsyncMock(return_value="Sukumar")

    text = await service.expiring_policies_within_days(days=5)

    assert "📅 Policies Expiring in Next 5 Days" in text
    assert "Policy: POL-4321" in text
    assert "Customer: Sukumar" in text
    assert "Days Remaining: 3" in text
    service.insurance.list_policies.assert_awaited_once_with(607, status="active")


@pytest.mark.asyncio
async def test_expiring_policies_within_days_empty_state():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)
    service.insurance.list_policies = AsyncMock(return_value=[])

    text = await service.expiring_policies_within_days(days=10)

    assert text == "✅ No policies are expiring in the next 10 days."
