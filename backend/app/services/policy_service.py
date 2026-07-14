from datetime import UTC, datetime, time
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verticals import InsurancePolicy
from app.services.audit_service import write_audit_event
from app.services.insurance_service import InsuranceService
from app.utils.datetime_utils import normalize_to_utc_naive
from app.utils.policy_queries import select_insurance_policies


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PolicyService:
    """Adapter that forwards policy operations to the canonical InsuranceService
    and normalizes premium units between Decimal (API) and integer cents (DB).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._svc = InsuranceService(session)

    async def create_policy(self, *, organization_id: int, policyholder_name: str, policy_number: str, expiry_date: datetime, premium: Decimal | None = None, currency: str | None = None, policy_type: str | None = None, carrier: str | None = None, renewal_frequency: str | None = None, grace_period_days: int | None = None, assigned_agent_id: int | None = None, preferred_channel: list[str] | str | None = None, reminder_type: str | None = "default", reminder_unit: str | None = None, reminder_value: int | None = None, dnd_start_time: time | str | None = None, dnd_end_time: time | str | None = None, custom_reminders: list | None = None, policy_metadata: str | None = None, actor_user_id: int | None = None, contact_phone: str | None = None, contact_email: str | None = None) -> InsurancePolicy:
        premium_int = None
        if premium is not None:
            # Store premium exactly as provided (no cents conversion)
            premium_int = int(Decimal(premium))
        expiry_date = normalize_to_utc_naive(expiry_date)
        policy = await self._svc.create_policy(
            organization_id=organization_id,
            policyholder_name=policyholder_name,
            expiry_date=expiry_date,
            actor_user_id=actor_user_id,
            policy_number=policy_number,
            premium=premium_int or 0,
            policy_type=policy_type,
            carrier=carrier,
            renewal_frequency=renewal_frequency,
            grace_period_days=grace_period_days,
            assigned_agent_user_id=assigned_agent_id,
            preferred_channel=preferred_channel,
            reminder_type=reminder_type,
            reminder_unit=reminder_unit,
            reminder_value=reminder_value,
            dnd_start_time=dnd_start_time,
            dnd_end_time=dnd_end_time,
            custom_reminders=custom_reminders,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        # convert stored integer -> Decimal for API consumers (no cents conversion)
        if getattr(policy, "premium", None) is not None:
            policy.premium = Decimal(policy.premium)
        return policy

    async def get_policy(self, policy_id: int) -> InsurancePolicy:
        result = await self.session.execute(
            select_insurance_policies(load_custom_reminders=True).where(
                InsurancePolicy.id == policy_id
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise ValueError("policy not found")
        if getattr(item, "premium", None) is not None:
            item.premium = Decimal(item.premium)
        return item

    async def list_policies(self, organization_id: int, status: str | None = None) -> list[InsurancePolicy]:
        rows = await self._svc.list_policies(organization_id=organization_id, status=status)
        for p in rows:
            if getattr(p, "premium", None) is not None:
                p.premium = Decimal(p.premium)
        return rows

    async def update_policy(self, policy_id: int, updates: dict, actor_user_id: int | None = None) -> InsurancePolicy:
        # map API-friendly keys to DB fields
        if "assigned_agent_id" in updates:
            updates["assigned_agent_user_id"] = updates.pop("assigned_agent_id")
        if "premium" in updates and updates["premium"] is not None:
            # Store premium exactly as provided (no cents conversion)
            updates["premium"] = int(Decimal(updates["premium"]))
        item = await self._svc.update_policy(policy_id, updates)
        if getattr(item, "premium", None) is not None:
            item.premium = Decimal(item.premium)
        return item

    async def delete_policy(self, policy_id: int, actor_user_id: int | None = None) -> None:
        item = await self.session.get(InsurancePolicy, policy_id)
        if item is None:
            raise ValueError("policy not found")
        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="policy.deleted",
            entity_type="policy",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.delete(item)
        await self.session.commit()

    async def renew_policy(self, policy_id: int, actor_user_id: int | None = None) -> InsurancePolicy:
        item = await self._svc.mark_policy_renewed(policy_id=policy_id, actor_user_id=actor_user_id)
        if getattr(item, "premium", None) is not None:
            item.premium = Decimal(item.premium)
        return item

    async def renew_policy_with_new_expiry(
        self,
        policy_id: int,
        *,
        new_expiry_date: datetime,
        renewal_notes: str | None = None,
        actor_user_id: int | None = None,
    ) -> tuple[InsurancePolicy, list]:
        new_expiry_date = normalize_to_utc_naive(new_expiry_date)
        policy, reminders = await self._svc.renew_policy_with_new_expiry(
            policy_id=policy_id,
            new_expiry_date=new_expiry_date,
            renewal_notes=renewal_notes,
            actor_user_id=actor_user_id,
        )
        if getattr(policy, "premium", None) is not None:
            policy.premium = Decimal(policy.premium)
        return policy, reminders

    async def list_policy_reminders(self, policy_id: int) -> list:
        return await self._svc.list_policy_reminders(policy_id)
