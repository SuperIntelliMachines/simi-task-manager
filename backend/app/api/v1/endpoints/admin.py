from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List
from datetime import datetime
import logging
import re

from app.api.deps import PermissionChecker, get_current_active_admin
from app.core.database import Base, get_db_session
from app.core.config import get_settings
from app.core.organization_dependency_labels import (
    RELATED_BUSINESS_DATA_LABEL,
    build_dependency_items,
    label_for_table,
    organization_dependency_conflict_detail,
)
from app.core.permissions import (
    ADMIN_CREATE,
    ADMIN_DELETE,
    ADMIN_ONBOARD,
    ADMIN_UPDATE,
    ADMIN_VIEW,
    USERS_CREATE,
    USERS_INVITE,
    USERS_UPDATE,
    USERS_VIEW,
)
from app.models.core import (
    Organization,
    User,
    ReminderAttempt,
    WorkflowTemplate,
    WorkflowRun,
    Task,
)
from app.models.atm017 import MessageTemplate, NotificationPreference
from app.models.atm012 import AgentDefinition, AgentInvocation
from app.services.audit_service import write_audit_event
from app.api.v1.schemas.admin import (
    CustomerCreate,
    CustomerOut,
    OnboardOut,
    HealthUsageOut,
    UsageOut,
    AuditLogOut,
    ReminderAttemptOut,
    AgentInvocationOut,
    SupportAccessOut,
)
from app.models.atm017 import AuditEvent
from app.models.atm012 import AgentInvocation
from app.models.support_access_sessions import SupportAccessSession
from app.models.rbac import Permission, Role, RolePermission
from app.models.auth_security import LoginAudit
from app.services.rbac_service import RBACService
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.core.security import get_password_hash

router = APIRouter(
    dependencies=[Depends(get_current_active_admin)],
)
settings = get_settings()
logger = logging.getLogger(__name__)

# ORM-managed children that SQLAlchemy cascades on organization delete.
_ORG_CASCADE_CHILD_TABLES = frozenset({"support_access_sessions"})


def _organization_fk_dependencies() -> list[tuple[str, str, str | None]]:
    """Return (table_name, column_name, constraint_name) for FKs pointing at organizations."""
    deps: list[tuple[str, str, str | None]] = []
    for table in Base.metadata.sorted_tables:
        if table.name == "organizations":
            continue
        for fk in table.foreign_keys:
            if fk.column.table.name != "organizations":
                continue
            constraint_name = fk.constraint.name if fk.constraint is not None else None
            deps.append((table.name, fk.parent.name, constraint_name))
    return deps


async def _find_blocking_organization_dependencies(
    session: AsyncSession,
    organization_id: int,
) -> list[dict[str, object]]:
    blocking: list[dict[str, object]] = []
    for table_name, column_name, constraint_name in _organization_fk_dependencies():
        if table_name in _ORG_CASCADE_CHILD_TABLES:
            continue
        # Identifiers come from SQLAlchemy metadata, not user input.
        count = (
            await session.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" = :organization_id'),
                {"organization_id": organization_id},
            )
        ).scalar_one()
        if int(count or 0) > 0:
            blocking.append(
                {
                    "table": table_name,
                    "column": column_name,
                    "constraint": constraint_name,
                    "count": int(count),
                }
            )
    return blocking


def _parse_fk_violation(error: IntegrityError) -> tuple[str | None, str | None]:
    """Best-effort extract of blocking table/constraint from DB error text."""
    message = str(getattr(error, "orig", None) or error)
    table_match = re.search(r'on table ["\']?([a-zA-Z0-9_]+)["\']?', message)
    constraint_match = re.search(
        r'(?:constraint|FOREIGN KEY constraint failed)[:\s]*["\']?([a-zA-Z0-9_]+)["\']?',
        message,
        flags=re.IGNORECASE,
    )
    table = table_match.group(1) if table_match else None
    constraint = constraint_match.group(1) if constraint_match else None
    if table is None:
        referenced = re.search(r'referenced from table ["\']?([a-zA-Z0-9_]+)["\']?', message)
        if referenced:
            table = referenced.group(1)
    return table, constraint


def _serialize_model(obj):
    data = {}
    for k, v in obj.__dict__.items():
        if k.startswith("_"):
            continue
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
        else:
            data[k] = v
    return data


@router.get("/customers", response_model=List[CustomerOut], dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def list_customers(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Organization))
    orgs = result.scalars().all()
    return [_serialize_model(o) for o in orgs]


@router.post("/customers", response_model=CustomerOut, dependencies=[Depends(PermissionChecker(ADMIN_CREATE))])
async def create_customer(customer_in: dict, session: AsyncSession = Depends(get_db_session)):
    # basic validation
    name = customer_in.get("name") if isinstance(customer_in, dict) else None
    if not name or not isinstance(name, str) or len(name) > 255:
        raise HTTPException(status_code=400, detail="Invalid or missing customer name")
    # validate uniqueness
    existing = await session.execute(select(Organization).where(Organization.name == name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Customer with this name already exists")
    now = datetime.utcnow()
    org = Organization(name=name, created_at=now, updated_at=now)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return _serialize_model(org)


@router.get("/customers/{organization_id}", response_model=CustomerOut, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_customer(organization_id: int, session: AsyncSession = Depends(get_db_session)):
    org = await session.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize_model(org)


@router.patch("/customers/{organization_id}", response_model=CustomerOut, dependencies=[Depends(PermissionChecker(ADMIN_UPDATE))])
async def update_customer(organization_id: int, customer_in: dict, session: AsyncSession = Depends(get_db_session)):
    org = await session.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer not found")
    # only allow updating name for now
    name = customer_in.get("name") if isinstance(customer_in, dict) else None
    if name:
        if not isinstance(name, str) or len(name) > 255:
            raise HTTPException(status_code=400, detail="Invalid customer name")
        # check uniqueness
        q = await session.execute(select(Organization).where(Organization.name == name, Organization.id != organization_id))
        if q.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="Customer with this name already exists")
        org.name = name
    org.updated_at = datetime.utcnow()
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return _serialize_model(org)


@router.post("/customers/{organization_id}/onboard", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_ONBOARD))])
async def onboard_customer(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> OnboardOut:
    # Verify organization exists
    org = await session.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.utcnow()

    # Create or get owner user
    owner_email = f"owner+{organization_id}@example.com"
    owner_q = await session.execute(select(User).where(User.organization_id == organization_id, User.email == owner_email))
    owner = owner_q.scalar_one_or_none()
    if owner is None:
        owner = User(
            organization_id=organization_id,
            email=owner_email,
            hashed_password="",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(owner)
        await session.commit()
        await session.refresh(owner)
        await write_audit_event(
            session=session,
            organization_id=organization_id,
            actor_user_id=None,
            event_type="customer.onboard.user_created",
            entity_type="user",
            entity_id=str(owner.id),
            payload={"email": owner.email},
        )

    # Create a default agent definition for the org
    agent_key = "general-task-agent"
    agent_q = await session.execute(select(AgentDefinition).where(AgentDefinition.organization_id == organization_id, AgentDefinition.key == agent_key))
    agent_def = agent_q.scalar_one_or_none()
    if agent_def is None:
        agent_def = AgentDefinition(
            organization_id=organization_id,
            key=agent_key,
            name="General Task Agent",
            domain="general",
            description="Default general task agent",
            created_at=now,
            updated_at=now,
        )
        session.add(agent_def)
        await session.commit()
        await session.refresh(agent_def)
        await write_audit_event(
            session=session,
            organization_id=organization_id,
            actor_user_id=owner.id,
            event_type="customer.onboard.agent_created",
            entity_type="agent_definition",
            entity_id=str(agent_def.id),
            payload={"key": agent_def.key},
        )

    # Create a default message template
    mt_name = "default-reminder"
    mt_q = await session.execute(select(MessageTemplate).where(MessageTemplate.organization_id == organization_id, MessageTemplate.name == mt_name))
    mt = mt_q.scalar_one_or_none()
    if mt is None:
        mt = MessageTemplate(
            organization_id=organization_id,
            name=mt_name,
            channel="whatsapp",
            purpose="reminder",
            status="approved",
            body="Reminder: {{title}}",
            required_variables=["title"],
            created_at=now,
            updated_at=now,
        )
        session.add(mt)
        await session.commit()
        await session.refresh(mt)
        await write_audit_event(
            session=session,
            organization_id=organization_id,
            actor_user_id=owner.id,
            event_type="customer.onboard.message_template_created",
            entity_type="message_template",
            entity_id=str(mt.id),
            payload={"name": mt.name},
        )

    # Create notification preference for owner
    pref_q = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == organization_id,
            NotificationPreference.user_id == owner.id,
            NotificationPreference.purpose == "reminder",
        )
    )
    pref = pref_q.scalar_one_or_none()
    if pref is None:
        pref = NotificationPreference(
            organization_id=organization_id,
            user_id=owner.id,
            purpose="reminder",
            preferred_channel="whatsapp",
            opt_out=False,
            created_at=now,
            updated_at=now,
        )
        session.add(pref)
        await session.commit()
        await session.refresh(pref)

    # Create a sample workflow template and run
    wf_name = "welcome-workflow"
    wf_q = await session.execute(select(WorkflowTemplate).where(WorkflowTemplate.organization_id == organization_id, WorkflowTemplate.name == wf_name))
    wf = wf_q.scalar_one_or_none()
    if wf is None:
        wf = WorkflowTemplate(
            organization_id=organization_id,
            name=wf_name,
            version=1,
            definition="[{\"step\": \"create_task\"}]",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)

    # Create a sample task and workflow run
    task = Task(
        organization_id=organization_id,
        title="Welcome task",
        description="This is a sample task created during onboarding",
        domain="general",
        status="open",
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    wf_run = WorkflowRun(
        organization_id=organization_id,
        workflow_template_id=wf.id,
        task_id=task.id,
        status="completed",
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(wf_run)
    await session.commit()
    await session.refresh(wf_run)

    # Record a sample agent invocation
    ai = AgentInvocation(
        organization_id=organization_id,
        actor_user_id=owner.id,
        agent=agent_def.key,
        domain=agent_def.domain,
        intent="sample_onboard",
        confidence=1.0,
        input_summary="Run onboarding",
        output_summary="Onboarding completed",
        guardrail_result="ok",
        tool_calls=[],
        token_usage={},
        created_at=now,
    )
    session.add(ai)
    await session.commit()
    await session.refresh(ai)

    await write_audit_event(
        session=session,
        organization_id=organization_id,
        actor_user_id=owner.id,
        event_type="customer.onboard.completed",
        entity_type="organization",
        entity_id=str(organization_id),
        payload={"owner_id": owner.id},
    )

    return {
        "owner_user": {"id": owner.id, "email": owner.email},
        "agents_enabled": True,
        "workflows_configured": True,
        "message_templates_configured": True,
        "sample_workflow_run": True,
    }


@router.get("/customers/{organization_id}/health", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_customer_health(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> HealthUsageOut:
    # Simple health metrics: count users and agent invocations
    users_q = await session.execute(select(func.count()).select_from(User).where(User.organization_id == organization_id))
    users_count = users_q.scalar_one()
    inv_q = await session.execute(select(func.count()).select_from(AgentInvocation).where(AgentInvocation.organization_id == organization_id))
    inv_count = inv_q.scalar_one()
    health_score = 100 if users_count > 0 else 50
    return {"health_score": health_score, "active_users": users_count, "agent_invocations": inv_count}


@router.get("/customers/{organization_id}/usage", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_customer_usage(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> UsageOut:
    # Simple usage: count agent invocations as monthly requests
    inv_q = await session.execute(select(func.count()).select_from(AgentInvocation).where(AgentInvocation.organization_id == organization_id))
    monthly_requests = inv_q.scalar_one()
    return {"monthly_requests": monthly_requests, "storage_used": "0MB"}


@router.get("/customers/{organization_id}/audit", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_customer_audit(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    result = await session.execute(select(AuditEvent).where(AuditEvent.organization_id == organization_id).order_by(AuditEvent.created_at.desc()))
    logs = result.scalars().all()
    return {"audit_logs": [ _serialize_model(l) for l in logs ]}


@router.get("/customers/{organization_id}/failed-reminders", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_failed_reminders(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    # Return failed reminder attempts for the organization
    result = await session.execute(
        select(ReminderAttempt)
        .where(
            ReminderAttempt.organization_id == organization_id,
            ReminderAttempt.status == "failed",
        )
        .order_by(ReminderAttempt.created_at.desc())
    )
    attempts = result.scalars().all()
    return {"failed_reminders": [ _serialize_model(a) for a in attempts ]}


@router.get("/customers/{organization_id}/agent-invocations", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_agent_invocation_list(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    result = await session.execute(select(AgentInvocation).where(AgentInvocation.organization_id == organization_id).order_by(AgentInvocation.created_at.desc()))
    invs = result.scalars().all()
    return {"invocations": [ _serialize_model(i) for i in invs ]}


@router.get("/customers/{organization_id}/support-access", response_model=dict, dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_support_access(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    result = await session.execute(select(SupportAccessSession).where(SupportAccessSession.organization_id == organization_id).order_by(SupportAccessSession.created_at.desc()))
    sessions = result.scalars().all()
    return {"access_sessions": [ _serialize_model(s) for s in sessions ]}



class InviteIn(BaseModel):
    email: str
    password: str
    tenant: str


@router.post("/invite", response_model=dict, dependencies=[Depends(PermissionChecker(USERS_INVITE))])
async def invite_user(invite: InviteIn, session: AsyncSession = Depends(get_db_session)):
    # Ensure tenant exists (create if missing)
    now = datetime.utcnow()
    try:
        org = None
        q = await session.execute(select(Organization).where(Organization.name == invite.tenant))
        org = q.scalar_one_or_none()
        if org is None:
            org = Organization(name=invite.tenant, created_at=now, updated_at=now)
            session.add(org)
            await session.commit()
            await session.refresh(org)

        # create user
        existing = await session.execute(select(User).where(User.email == invite.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="User already exists")

        hashed = get_password_hash(invite.password)
        user = User(organization_id=org.id, email=invite.email, hashed_password=hashed, is_active=True, created_at=now, updated_at=now)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # return a frontend path to use as an invite link (frontend will build full URL)
        return {"invite_path": f"/login?invited_email={invite.email}"}
    except IntegrityError:
        await session.rollback()
        # try to recover organization if it was created concurrently
        q = await session.execute(select(Organization).where(Organization.name == invite.tenant))
        org = q.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=500, detail="Failed to create organization")
        # try to create user again
        try:
            existing = await session.execute(select(User).where(User.email == invite.email))
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(status_code=400, detail="User already exists")
            hashed = get_password_hash(invite.password)
            user = User(organization_id=org.id, email=invite.email, hashed_password=hashed, is_active=True, created_at=now, updated_at=now)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return {"invite_path": f"/login?invited_email={invite.email}"}
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class PlatformUserCreateIn(BaseModel):
    email: str
    password: str
    organization_id: int
    role: str = "tenant_user"


class PlatformUserUpdateIn(BaseModel):
    organization_id: int | None = None
    role: str | None = None
    is_active: bool | None = None


class PlatformUserResetPasswordIn(BaseModel):
    new_password: str


class PlatformRoleCreateIn(BaseModel):
    name: str
    description: str | None = None


class PlatformRolePermissionsIn(BaseModel):
    permission_codes: list[str]


@router.get("/platform/stats", dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def get_platform_stats(session: AsyncSession = Depends(get_db_session)) -> dict:
    org_count = (await session.execute(select(func.count()).select_from(Organization))).scalar_one()
    user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    active_user_count = (
        await session.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar_one()
    active_org_count = (
        await session.execute(
            select(func.count(func.distinct(User.organization_id))).where(User.is_active.is_(True))
        )
    ).scalar_one()
    agent_count = (await session.execute(select(func.count()).select_from(AgentDefinition))).scalar_one()
    task_count = (await session.execute(select(func.count()).select_from(Task))).scalar_one()
    return {
        "total_organizations": org_count,
        "total_users": user_count,
        "active_users": active_user_count,
        "active_organizations": active_org_count,
        "total_agents": agent_count,
        "total_tasks": task_count,
        "system_status": "healthy",
    }


@router.get("/users", dependencies=[Depends(PermissionChecker(USERS_VIEW))])
async def list_platform_users(session: AsyncSession = Depends(get_db_session)) -> dict:
    result = await session.execute(
        select(User, Organization.name)
        .join(Organization, Organization.id == User.organization_id)
        .order_by(User.created_at.desc())
    )
    users = []
    for row in result.all():
        user, org_name = row
        users.append(
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "organization_id": user.organization_id,
                "organization_name": org_name,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )
    return {"users": users}


@router.post("/users", dependencies=[Depends(PermissionChecker(USERS_CREATE))])
async def create_platform_user(body: PlatformUserCreateIn, session: AsyncSession = Depends(get_db_session)) -> dict:
    org = await session.get(Organization, body.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    existing = await session.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="User already exists")
    now = datetime.utcnow()
    user = User(
        organization_id=body.organization_id,
        email=body.email.lower(),
        hashed_password=get_password_hash(body.password),
        role=body.role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": org.name,
        "is_active": user.is_active,
    }


@router.patch("/users/{user_id}", dependencies=[Depends(PermissionChecker(USERS_UPDATE))])
async def update_platform_user(
    user_id: int,
    body: PlatformUserUpdateIn,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.organization_id is not None:
        org = await session.get(Organization, body.organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        user.organization_id = body.organization_id
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    org = await session.get(Organization, user.organization_id)
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": bool(user.is_active),
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
    }


@router.post("/users/{user_id}/reset-password", dependencies=[Depends(PermissionChecker(USERS_UPDATE))])
async def reset_platform_user_password(
    user_id: int,
    body: PlatformUserResetPasswordIn,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    return {"detail": "Password reset successfully"}


@router.delete("/customers/{organization_id}", dependencies=[Depends(PermissionChecker(ADMIN_DELETE))])
async def delete_customer(organization_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    org = await session.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer not found")

    user_count = (
        await session.execute(select(func.count()).select_from(User).where(User.organization_id == organization_id))
    ).scalar_one()
    if user_count > 0:
        logger.warning(
            "Blocked organization delete id=%s name=%s due to users count=%s table=users",
            organization_id,
            org.name,
            user_count,
        )
        raise HTTPException(
            status_code=409,
            detail=organization_dependency_conflict_detail(
                [{"label": label_for_table("users"), "count": int(user_count)}]
            ),
        )

    blocking = await _find_blocking_organization_dependencies(session, organization_id)
    if blocking:
        logger.warning(
            "Blocked organization delete id=%s name=%s due to related records: %s",
            organization_id,
            org.name,
            blocking,
        )
        raise HTTPException(
            status_code=409,
            detail=organization_dependency_conflict_detail(build_dependency_items(blocking)),
        )

    try:
        await session.delete(org)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        table, constraint = _parse_fk_violation(exc)
        logger.exception(
            "IntegrityError deleting organization id=%s name=%s blocking_table=%s constraint=%s",
            organization_id,
            org.name,
            table,
            constraint,
        )
        dependencies: list[dict[str, object]] = []
        if table:
            dependencies = [{"label": label_for_table(table), "count": 1}]
        else:
            dependencies = [{"label": RELATED_BUSINESS_DATA_LABEL, "count": 1}]
        raise HTTPException(
            status_code=409,
            detail=organization_dependency_conflict_detail(dependencies),
        ) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.exception(
            "Database error deleting organization id=%s name=%s",
            organization_id,
            org.name,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete organization due to a database error.",
        ) from exc

    return {"detail": "Organization deleted"}


@router.get("/roles", dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def list_platform_roles(session: AsyncSession = Depends(get_db_session)) -> dict:
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
    )
    roles = list(result.scalars().all())
    return {
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": bool(role.is_system),
                "permissions": [p.code for p in role.permissions],
            }
            for role in roles
        ]
    }


@router.post("/roles", dependencies=[Depends(PermissionChecker(ADMIN_CREATE))])
async def create_platform_role(body: PlatformRoleCreateIn, session: AsyncSession = Depends(get_db_session)) -> dict:
    name = body.name.strip().lower().replace(" ", "_")
    if not name:
        raise HTTPException(status_code=400, detail="Role name is required")
    existing = await session.execute(select(Role).where(Role.name == name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Role already exists")
    role = Role(name=name, description=body.description, is_system=False, created_at=datetime.utcnow())
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return {"id": role.id, "name": role.name, "description": role.description, "is_system": False, "permissions": []}


@router.put("/roles/{role_id}/permissions", dependencies=[Depends(PermissionChecker(ADMIN_UPDATE))])
async def update_role_permissions(
    role_id: int,
    body: PlatformRolePermissionsIn,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be modified from the platform UI")

    perms_result = await session.execute(select(Permission))
    all_perms = {p.code: p for p in perms_result.scalars().all()}
    requested = set(body.permission_codes)
    unknown = requested - set(all_perms.keys())
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {', '.join(sorted(unknown))}")

    await session.execute(
        RolePermission.__table__.delete().where(RolePermission.role_id == role_id)
    )
    for code in requested:
        perm = all_perms[code]
        session.add(RolePermission(role_id=role_id, permission_id=perm.id))
    await session.commit()

    refreshed = await session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = refreshed.scalar_one()
    return {
        "id": role.id,
        "name": role.name,
        "permissions": [p.code for p in role.permissions],
    }


@router.get("/permissions", dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def list_platform_permissions(session: AsyncSession = Depends(get_db_session)) -> dict:
    rbac = RBACService(session)
    permissions = await rbac.list_permissions()
    return {
        "permissions": [
            {
                "id": p.id,
                "module": p.module,
                "permission": p.permission,
                "code": p.code,
                "description": p.description,
            }
            for p in permissions
        ]
    }


@router.get("/audit", dependencies=[Depends(PermissionChecker(ADMIN_VIEW))])
async def list_platform_audit_logs(
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    capped = min(max(limit, 1), 500)
    audit_result = await session.execute(
        select(LoginAudit).order_by(LoginAudit.created_at.desc()).limit(capped)
    )
    login_logs = [
        {
            "id": row.id,
            "source": "login_audit",
            "email": row.email,
            "success": row.success,
            "failure_reason": row.failure_reason,
            "ip_address": row.ip_address,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in audit_result.scalars().all()
    ]
    event_result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(capped)
    )
    event_logs = [
        {
            "id": row.id,
            "source": "audit_event",
            "organization_id": row.organization_id,
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in event_result.scalars().all()
    ]
    combined = sorted(
        login_logs + event_logs,
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )[:capped]
    return {"audit_logs": combined}
