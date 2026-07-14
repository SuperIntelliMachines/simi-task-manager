from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from decimal import Decimal
from datetime import datetime as _dt, timezone
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user, resolve_organization_scope
from app.core.database import get_db_session
from app.core.permissions import (
    INSURANCE_CREATE,
    INSURANCE_DELETE,
    INSURANCE_UPDATE,
    INSURANCE_VIEW,
    LEADS_CREATE,
    LEADS_DELETE,
    LEADS_UPDATE,
    LEADS_VIEW,
)
from app.models.core import Contact
from app.models.verticals import InsurancePolicy
from app.schemas.atm007 import (
    InsuranceLeadCreateBody,
    InsuranceLeadPatchBody,
    InsuranceLeadWorkflowStartBody,
    InsurancePolicyCreateBody,
    InsurancePolicyPatchBody,
    InsuranceWorkflowStartBody,
)
from app.services.insurance_service import InsuranceService
from app.services.policy_document_service import PolicyDocumentUploadError, save_policy_document
from app.services.policy_service import PolicyService
from app.services.followup_service import FollowUpService
from app.utils.policy_response import policy_response_from_model
from app.schemas.insurance import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyDocumentUploadResponse,
    PolicyRenewalSmsResponse,
    PolicyRenewRequest,
    PolicyRenewResponse,
    PolicyReminderResponse,
    FollowUpCreate,
    FollowUpUpdate,
    FollowUpResponse,
)
from fastapi import status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/insurance",
    tags=["insurance"],
    dependencies=[Depends(get_current_user)],
)
logger = logging.getLogger(__name__)


def _serialize(item):
    data = {}
    for key, value in item.__dict__.items():
        if key.startswith("_"):
            continue
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data


async def _attach_contact_fields(session: AsyncSession, policy_row) -> None:
    contact = await session.get(Contact, policy_row.policyholder_id)
    if contact is None:
        return
    setattr(policy_row, "policyholder_name", contact.name)
    setattr(policy_row, "mobile", contact.phone)
    policy_email = getattr(policy_row, "email", None)
    setattr(policy_row, "email", (policy_email or "").strip() or contact.email)


def _pick_policy_for_lead(
    policies: list[InsurancePolicy],
    related_policy_id: int | None,
) -> InsurancePolicy | None:
    """Prefer related policy, then first active, then latest by created_at."""
    if related_policy_id is not None:
        for policy in policies:
            if policy.id == related_policy_id:
                return policy
    if not policies:
        return None
    active = [p for p in policies if (p.status or "").lower() == "active"]
    pool = active if active else list(policies)
    return max(pool, key=lambda p: (p.created_at, p.id))


def _lead_policy_type_from_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    for line in notes.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("policy type:"):
            return stripped.split(":", 1)[1].strip() or None
    return None


async def _followups_to_responses(session: AsyncSession, rows: list) -> list[FollowUpResponse]:
    """Enrich leads with contact + policy data (contact_id → policyholder_id)."""
    contact_ids = {r.contact_id for r in rows if getattr(r, "contact_id", None)}
    contacts_by_id: dict[int, Contact] = {}
    policies_by_holder: dict[int, list[InsurancePolicy]] = {}

    if contact_ids:
        contact_result = await session.execute(select(Contact).where(Contact.id.in_(contact_ids)))
        contacts_by_id = {c.id: c for c in contact_result.scalars().all()}

        policy_result = await session.execute(
            select(InsurancePolicy).where(InsurancePolicy.policyholder_id.in_(contact_ids))
        )
        for policy in policy_result.scalars().all():
            policies_by_holder.setdefault(policy.policyholder_id, []).append(policy)

    responses: list[FollowUpResponse] = []
    for row in rows:
        contact = contacts_by_id.get(row.contact_id) if row.contact_id else None
        customer_name = contact.name if contact else None
        contact_phone = contact.phone if contact else None
        contact_email = contact.email if contact else None

        holder_policies = policies_by_holder.get(row.contact_id, []) if row.contact_id else []
        related_id = getattr(row, "related_policy_id", None)
        matched_policy = _pick_policy_for_lead(holder_policies, related_id)
        policy_type = matched_policy.policy_type if matched_policy else _lead_policy_type_from_notes(getattr(row, "notes", None))

        base = FollowUpResponse.model_validate(row)
        responses.append(
            base.model_copy(
                update={
                    "customerName": customer_name,
                    "contact_name": customer_name,
                    "contact_phone": contact_phone,
                    "contact_email": contact_email,
                    "email": contact_email,
                    "phone": contact_phone,
                    "policyType": policy_type,
                    "followUpDate": getattr(row, "followup_due_at", None),
                }
            )
        )
    return responses


@router.post("/policies", dependencies=[Depends(PermissionChecker(INSURANCE_CREATE))])
async def create_policy(body: InsurancePolicyCreateBody, session: AsyncSession = Depends(get_db_session)):
    service = PolicyService(session)
    logger.info(
        "[create_policy API] reminder_type=%s dnd_start_time=%s dnd_end_time=%s custom_reminders=%s",
        body.reminder_type,
        body.dnd_start_time,
        body.dnd_end_time,
        [item.model_dump() for item in body.custom_reminders] if body.custom_reminders else None,
    )
    try:
        # ensure expiry is a datetime
        expiry = body.expiry_date if isinstance(body.expiry_date, _dt) else _dt.combine(body.expiry_date, _dt.min.time())
        # normalize timezone-aware datetimes to UTC naive
        if getattr(expiry, "tzinfo", None) is not None:
            expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
        # pass premium through (PolicyService will store premium as provided)
        premium_decimal = body.premium
        policy = await service.create_policy(
            organization_id=body.organization_id,
            policyholder_name=body.policyholder_name,
            policy_number=body.policy_number,
            expiry_date=expiry,
            premium=premium_decimal,
            policy_type=body.policy_type,
            carrier=body.carrier,
            renewal_frequency=body.renewal_frequency,
            grace_period_days=body.grace_period_days,
            assigned_agent_id=body.assigned_agent_user_id,
            preferred_channel=body.preferred_channel,
            reminder_type=body.reminder_type,
            reminder_unit=body.reminder_unit,
            reminder_value=body.reminder_value,
            dnd_start_time=body.dnd_start_time,
            dnd_end_time=body.dnd_end_time,
            custom_reminders=(
                [item.model_dump() for item in body.custom_reminders]
                if body.custom_reminders
                else None
            ),
            actor_user_id=body.actor_user_id,
            contact_phone=body.mobile_number,
            contact_email=body.email,
        )
        if body.document_name is not None or body.document_path is not None or body.mobile_number is not None:
            policy = await service.update_policy(
                policy.id,
                {
                    **({"document_name": body.document_name} if body.document_name is not None else {}),
                    **({"document_path": body.document_path} if body.document_path is not None else {}),
                    **({"mobile_number": body.mobile_number} if body.mobile_number is not None else {}),
                },
                actor_user_id=body.actor_user_id,
            )
    except ValueError as exc:
        if str(exc) == "Policy number already exists.":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        await _attach_contact_fields(session, policy)
    except Exception:
        pass
    return policy_response_from_model(policy)


@router.post("/policies/upload-document", response_model=PolicyDocumentUploadResponse, dependencies=[Depends(PermissionChecker(INSURANCE_CREATE))])
async def upload_policy_document(
    file: UploadFile = File(...),
    policy_id: int | None = Form(None),
):
    try:
        result = await save_policy_document(file, policy_id=policy_id)
    except PolicyDocumentUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PolicyDocumentUploadResponse.model_validate(result)


@router.get("/policies", dependencies=[Depends(PermissionChecker(INSURANCE_VIEW))])
async def list_policies(
    organization_id: int = Query(...),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    # keep existing InsuranceService behavior if present; also allow listing via PolicyService
    service = PolicyService(session)
    rows = await service.list_policies(organization_id=organization_id, status=status)
    for row in rows:
        try:
            await _attach_contact_fields(session, row)
        except Exception:
            continue
    return [policy_response_from_model(row) for row in rows]


@router.get("/policies/{policy_id}", response_model=PolicyResponse, dependencies=[Depends(PermissionChecker(INSURANCE_VIEW))])
async def get_policy(policy_id: int, session: AsyncSession = Depends(get_db_session)):
    service = PolicyService(session)
    try:
        item = await service.get_policy(policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _attach_contact_fields(session, item)
    return policy_response_from_model(item)


@router.put("/policies/{policy_id}", response_model=PolicyResponse, dependencies=[Depends(PermissionChecker(INSURANCE_UPDATE))])
async def put_policy(
    policy_id: int,
    body: PolicyUpdate,
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = PolicyService(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if body.custom_reminders is not None:
        updates["custom_reminders"] = [item.model_dump() for item in body.custom_reminders]
    try:
        # normalize expiry_date timezone if present
        if "expiry_date" in updates and getattr(updates["expiry_date"], "tzinfo", None) is not None:
            updates["expiry_date"] = updates["expiry_date"].astimezone(timezone.utc).replace(tzinfo=None)
        item = await service.update_policy(policy_id, updates, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _attach_contact_fields(session, item)
    return policy_response_from_model(item)


@router.delete("/policies/{policy_id}", dependencies=[Depends(PermissionChecker(INSURANCE_DELETE))])
async def delete_policy(
    policy_id: int,
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = PolicyService(session)
    try:
        await service.delete_policy(policy_id, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "deleted"}


@router.get("/policies/{policy_id}/reminders", response_model=list[PolicyReminderResponse], dependencies=[Depends(PermissionChecker(INSURANCE_VIEW))])
async def list_policy_reminders(
    policy_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    service = PolicyService(session)
    try:
        reminders = await service.list_policy_reminders(policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [PolicyReminderResponse.model_validate(row) for row in reminders]


@router.post("/policies/{policy_id}/renew", response_model=PolicyRenewResponse, dependencies=[Depends(PermissionChecker(INSURANCE_UPDATE))])
async def renew_policy(
    policy_id: int,
    body: PolicyRenewRequest | None = None,
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = PolicyService(session)
    try:
        if body is not None:
            policy, reminders = await service.renew_policy_with_new_expiry(
                policy_id,
                new_expiry_date=body.new_expiry_date,
                renewal_notes=body.renewal_notes,
                actor_user_id=actor_user_id,
            )
        else:
            policy = await service.renew_policy(policy_id, actor_user_id=actor_user_id)
            reminders = await service.list_policy_reminders(policy_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if "not found" in detail.lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc
    await _attach_contact_fields(session, policy)
    return PolicyRenewResponse(
        policy=policy_response_from_model(policy),
        reminders=[PolicyReminderResponse.model_validate(row) for row in reminders],
    )


@router.post("/policies/{policy_id}/renewal-sms", response_model=PolicyRenewalSmsResponse, dependencies=[Depends(PermissionChecker(INSURANCE_UPDATE))])
async def send_policy_renewal_sms(
    policy_id: int,
    actor_user_id: int | None = Query(None),
    logged_in_user_name: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = InsuranceService(session)
    try:
        result = await service.send_policy_renewal_sms(
            policy_id=policy_id,
            actor_user_id=actor_user_id,
            logged_in_user_name=logged_in_user_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PolicyRenewalSmsResponse.model_validate(result)


# Follow-up endpoints
@router.post("/followups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(PermissionChecker(LEADS_CREATE))])
async def create_followup(
    body: FollowUpCreate,
    organization_id: int = Query(...),
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = FollowUpService(session)
    try:
        # prefer contact_id if provided
        contact_name = body.contact_name if body.contact_id is None else None
        item = await service.create_followup(
            organization_id=organization_id,
            related_policy_id=body.related_policy_id,
            contact_id=body.contact_id,
            contact_name=contact_name,
            contact_email=body.contact_email,
            contact_phone=body.contact_phone,
            status=body.status,
            preferred_channel=body.preferred_channel,
            followup_due_at=body.followup_due_at,
            assigned_agent_id=body.assigned_agent_id,
            notes=body.notes,
            created_by=actor_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    enriched = await _followups_to_responses(session, [item])
    return enriched[0]


@router.get("/followups", response_model=list[FollowUpResponse], dependencies=[Depends(PermissionChecker(LEADS_VIEW))])
async def list_followups(
    organization_id: int = Query(...),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = FollowUpService(session)
    rows = await service.list_followups(organization_id=organization_id, status=status)
    return await _followups_to_responses(session, rows)


@router.get("/followups/{followup_id}", response_model=FollowUpResponse, dependencies=[Depends(PermissionChecker(LEADS_VIEW))])
async def get_followup(followup_id: int, session: AsyncSession = Depends(get_db_session)):
    service = FollowUpService(session)
    try:
        item = await service.get_followup(followup_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    enriched = await _followups_to_responses(session, [item])
    return enriched[0]


@router.put("/followups/{followup_id}", response_model=FollowUpResponse, dependencies=[Depends(PermissionChecker(LEADS_UPDATE))])
async def put_followup(
    followup_id: int,
    body: FollowUpUpdate,
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = FollowUpService(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        item = await service.update_followup(followup_id, updates, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    enriched = await _followups_to_responses(session, [item])
    return enriched[0]


@router.delete("/followups/{followup_id}", dependencies=[Depends(PermissionChecker(LEADS_DELETE))])
async def delete_followup(
    followup_id: int,
    actor_user_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    service = FollowUpService(session)
    try:
        await service.delete_followup(followup_id, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "deleted"}


@router.patch("/policies/{policy_id}", dependencies=[Depends(PermissionChecker(INSURANCE_UPDATE))])
async def patch_policy(
    policy_id: int,
    body: InsurancePolicyPatchBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = PolicyService(session)
    updates = {
        key: value
        for key, value in body.model_dump().items()
        if key != "actor_user_id" and value is not None
    }
    if body.custom_reminders is not None:
        updates["custom_reminders"] = [item.model_dump() for item in body.custom_reminders]
    try:
        item = await service.update_policy(policy_id, updates, actor_user_id=body.actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _attach_contact_fields(session, item)
    return policy_response_from_model(item)


@router.post("/policies/{policy_id}/renewal-workflow", dependencies=[Depends(PermissionChecker(INSURANCE_UPDATE))])
async def start_policy_workflow(
    policy_id: int,
    body: InsuranceWorkflowStartBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = InsuranceService(session)
    try:
        result = await service.start_policy_renewal_workflow(policy_id=policy_id, actor_user_id=body.actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {key: [_serialize(item) for item in value] if isinstance(value, list) else _serialize(value) for key, value in result.items()}


@router.post("/leads", dependencies=[Depends(PermissionChecker(LEADS_CREATE))])
async def create_lead(body: InsuranceLeadCreateBody, session: AsyncSession = Depends(get_db_session)):
    service = InsuranceService(session)
    try:
        lead = await service.create_lead(
            organization_id=body.organization_id,
            contact_name=body.contact_name,
            actor_user_id=body.actor_user_id,
            assigned_agent_user_id=body.assigned_agent_user_id,
            source=body.source,
            notes=body.notes,
            demo_logged_at=body.demo_logged_at,
            followup_due_at=body.followup_due_at,
            contact_phone=body.contact_phone,
            contact_email=body.contact_email,
            insurance_type=body.insurance_type,
            status=body.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info(
        "create_lead: org=%s contact=%s phone=%s email=%s followup_due_at=%s",
        body.organization_id,
        body.contact_name,
        body.contact_phone,
        body.contact_email,
        body.followup_due_at,
    )
    enriched = await _followups_to_responses(session, [lead])
    return enriched[0].model_dump(mode="json")


@router.patch("/leads/{lead_id}", dependencies=[Depends(PermissionChecker(LEADS_UPDATE))])
async def patch_lead(
    lead_id: int,
    body: InsuranceLeadPatchBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = InsuranceService(session)
    updates = {key: value for key, value in body.model_dump().items() if key != "actor_user_id" and value is not None}
    try:
        lead = await service.update_lead(lead_id, updates, actor_user_id=body.actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(lead)


@router.post("/leads/{lead_id}/follow-up-workflow", dependencies=[Depends(PermissionChecker(LEADS_UPDATE))])
async def start_lead_followup_workflow(
    lead_id: int,
    body: InsuranceLeadWorkflowStartBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = InsuranceService(session)
    try:
        logger.info("start_lead_followup_workflow called: lead_id=%s body=%s", lead_id, body.model_dump())
        result = await service.start_lead_followup_workflow(
            lead_id=lead_id,
            actor_user_id=body.actor_user_id,
            followup_due_at=body.followup_due_at,
            days_until_followup=body.days_until_followup,
        )
        logger.info("start_lead_followup_workflow result: lead=%s task=%s reminder=%s", getattr(result.get("lead"), "id", None), getattr(result.get("task"), "id", None), getattr(result.get("reminder"), "id", None))
    except ValueError as exc:
        logger.warning("start_lead_followup_workflow not found: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("start_lead_followup_workflow failed for lead_id=%s", lead_id)
        raise HTTPException(status_code=500, detail="failed to start lead follow-up workflow")
    return {key: _serialize(value) for key, value in result.items()}


@router.get("/dashboard", dependencies=[Depends(PermissionChecker(INSURANCE_VIEW))])
async def get_dashboard(
    organization_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
):
    service = InsuranceService(session)
    result = await service.get_dashboard(organization_id)
    pending = await _followups_to_responses(session, result["pending_followups"])
    return {
        "expiring_policies": [_serialize(row) for row in result.get("expiring_policies", [])],
        "due_renewals": [_serialize(row) for row in result["due_renewals"]],
        "grace_period_policies": [_serialize(row) for row in result.get("grace_period_policies", [])],
        "lapsed_policies": [_serialize(row) for row in result.get("lapsed_policies", [])],
        "pending_followups": [row.model_dump(mode="json") for row in pending],
        "counts": result["counts"],
        "policy_summary": result.get("policy_summary", {}),
        "lead_followup_overview": result.get("lead_followup_overview", {}),
        "renewal_intelligence": result.get("renewal_intelligence", {"points": [], "filters": {"agents": [], "product_types": []}}),
    }
