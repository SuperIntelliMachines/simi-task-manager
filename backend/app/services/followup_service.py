from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verticals import InsuranceLead
from app.services.audit_service import write_audit_event
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FollowUpService:
    """Adapter that reuses `InsuranceService` semantics but keeps the
    existing FollowUpService interface for callers.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._svc = InsuranceService(session)

    async def create_followup(self, *, organization_id: int, related_policy_id: int | None = None, contact_id: int | None = None, contact_name: str | None = None, contact_email: str | None = None, contact_phone: str | None = None, status: str | None = None, preferred_channel: str | None = None, followup_due_at: datetime | None = None, assigned_agent_id: int | None = None, notes: str | None = None, created_by: int | None = None) -> InsuranceLead:
        # If a contact_id is provided, create the lead directly referencing it.
        if contact_id is not None:
            now = utcnow_naive()
            from app.utils.datetime_utils import normalize_to_utc_naive

            followup_due_at = normalize_to_utc_naive(followup_due_at)
            lead = InsuranceLead(
                organization_id=organization_id,
                contact_id=contact_id,
                assigned_agent_user_id=assigned_agent_id,
                related_policy_id=related_policy_id,
                source=None,
                status=status or "open",
                notes=notes,
                demo_logged_at=None,
                followup_due_at=followup_due_at,
                created_at=now,
                updated_at=now,
            )
            self.session.add(lead)
            await self.session.commit()
            await self.session.refresh(lead)
            return lead
        # otherwise delegate to InsuranceService.create_lead which will resolve/create
        contact_name = contact_name or ""
        lead = await self._svc.create_lead(
            organization_id=organization_id,
            contact_name=contact_name,
            actor_user_id=created_by,
            assigned_agent_user_id=assigned_agent_id,
            related_policy_id=related_policy_id,
            source=None,
            notes=notes,
            demo_logged_at=None,
            followup_due_at=followup_due_at,
            contact_phone=contact_phone,
            contact_email=contact_email,
            status=status,
        )
        return lead

    async def get_followup(self, followup_id: int) -> InsuranceLead:
        item = await self.session.get(InsuranceLead, followup_id)
        if item is None:
            raise ValueError("followup not found")
        return item

    async def list_followups(self, organization_id: int, status: str | None = None) -> list[InsuranceLead]:
        return await self._svc.list_leads(organization_id=organization_id, status=status)

    async def update_followup(self, followup_id: int, updates: dict, actor_user_id: int | None = None) -> InsuranceLead:
        return await self._svc.update_lead(followup_id, updates, actor_user_id)

    async def delete_followup(self, followup_id: int, actor_user_id: int | None = None) -> None:
        item = await self.session.get(InsuranceLead, followup_id)
        if item is None:
            raise ValueError("followup not found")
        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="followup.deleted",
            entity_type="follow_up",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.delete(item)
        await self.session.commit()
