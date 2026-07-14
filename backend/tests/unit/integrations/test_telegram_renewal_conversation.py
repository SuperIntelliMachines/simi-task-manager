from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.telegram.insurance_commands import TelegramInsuranceCommandService
from app.integrations.telegram.parsers import parse_renewal_date
from app.integrations.telegram.renewal_context import renewal_context_store
from app.models.verticals import InsurancePolicy
from app.utils.datetime_utils import utcnow_naive


@pytest.fixture(autouse=True)
def clear_renewal_store():
    renewal_context_store._pending.clear()
    yield
    renewal_context_store._pending.clear()


@pytest.mark.asyncio
async def test_start_policy_renewal_prompts_for_date():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    old_expiry = utcnow_naive() - timedelta(days=30)
    policy = MagicMock(spec=InsurancePolicy)
    policy.id = 99
    policy.policyholder_id = 5
    policy.policy_number = "PI-0012"
    policy.status = "expired"
    policy.expiry_date = old_expiry

    service._find_latest_policy_for_customer = AsyncMock(return_value=policy)
    service._contact_name = AsyncMock(return_value="Ian")

    text = await service.start_policy_renewal(customer_name="Ian", external_user_id="user-1")

    assert "Policy Renewal Request" in text
    assert "Ian" in text
    assert "PI-0012" in text
    assert "Please provide the new expiry date" in text
    assert renewal_context_store.get("user-1") is not None
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_complete_policy_renewal_with_valid_date():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    old_expiry = utcnow_naive() - timedelta(days=30)
    policy = MagicMock(spec=InsurancePolicy)
    policy.id = 99
    policy.policyholder_id = 5
    policy.policy_number = "PI-0012"
    policy.status = "expired"
    policy.expiry_date = old_expiry

    service._find_latest_policy_for_customer = AsyncMock(return_value=policy)
    service._contact_name = AsyncMock(return_value="Ian")
    await service.start_policy_renewal(customer_name="Ian", external_user_id="user-1")
    session.get = AsyncMock(return_value=policy)

    renewed_policy = MagicMock(spec=InsurancePolicy)
    renewed_policy.id = 99
    renewed_policy.policy_number = "PI-0012"
    renewed_policy.status = "renewed"
    renewed_policy.expiry_date = parse_renewal_date("03-Jun-2027")
    service.insurance.mark_policy_renewed = AsyncMock(return_value=renewed_policy)

    text = await service.complete_policy_renewal(
        external_user_id="user-1",
        date_text="03-Jun-2027",
    )

    assert text is not None
    assert "Policy Renewed" in text
    assert "Ian" in text
    assert "PI-0012" in text
    assert "Previous Status: Expired" in text
    assert "New Status: Renewed" in text
    assert "03-Jun-2027" in text
    assert renewal_context_store.get("user-1") is None
    service.insurance.mark_policy_renewed.assert_awaited_once()
    call_kwargs = service.insurance.mark_policy_renewed.await_args.kwargs
    assert call_kwargs["policy_id"] == 99
    assert call_kwargs["new_expiry_date"] == parse_renewal_date("03-Jun-2027")


@pytest.mark.asyncio
async def test_complete_policy_renewal_invalid_date_reprompts():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    old_expiry = utcnow_naive() - timedelta(days=30)
    policy = MagicMock(spec=InsurancePolicy)
    policy.id = 99
    policy.policyholder_id = 5
    policy.policy_number = "PI-0012"
    policy.status = "expired"
    policy.expiry_date = old_expiry

    service._find_latest_policy_for_customer = AsyncMock(return_value=policy)
    service._contact_name = AsyncMock(return_value="Ian")
    await service.start_policy_renewal(customer_name="Ian", external_user_id="user-1")

    text = await service.complete_policy_renewal(
        external_user_id="user-1",
        date_text="not-a-date",
    )

    assert text is not None
    assert "Invalid date format" in text
    assert "Policy Renewal Request" in text
    assert renewal_context_store.get("user-1") is not None
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_renew_active_policy_returns_already_active_message():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)

    policy = MagicMock(spec=InsurancePolicy)
    policy.id = 99
    policy.policyholder_id = 5
    policy.policy_number = "PI-0012"
    policy.status = "active"
    policy.expiry_date = utcnow_naive() + timedelta(days=120)

    service._find_latest_policy_for_customer = AsyncMock(return_value=policy)
    service._contact_name = AsyncMock(return_value="Ian")

    text = await service.start_policy_renewal(customer_name="Ian", external_user_id="user-1")

    assert "Policy Already Active" in text
    assert renewal_context_store.get("user-1") is None


@pytest.mark.asyncio
async def test_start_policy_renewal_not_found():
    session = AsyncMock()
    service = TelegramInsuranceCommandService(session, organization_id=607)
    service._find_latest_policy_for_customer = AsyncMock(return_value=None)

    text = await service.start_policy_renewal(customer_name="Unknown", external_user_id="user-1")

    assert "No policy found for customer Unknown" in text


def test_parse_renewal_date_accepts_common_formats():
    assert parse_renewal_date("03-Jun-2027") is not None
    assert parse_renewal_date("June 3 2027") is not None
    assert parse_renewal_date("show dashboard") is None
