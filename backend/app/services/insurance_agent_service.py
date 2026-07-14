from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha1

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm005 import ContactChannelIdentity
from app.models.core import Contact, Task, User, WorkflowRun, WorkflowTemplate
from app.models.verticals import InsurancePolicy
from app.schemas.atm012 import AgentCommandInput, AgentExecutionResult, AgentStructuredResponse, ClarificationRequest, CreatedEntity
from app.utils.preferred_channels import resolve_policy_reminder_channels
from app.services.insurance_service import InsuranceService
from app.services.policy_service import PolicyService
from decimal import Decimal
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class InsuranceAgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_service = TaskService(session)
        self.reminder_service = ReminderService(session)
        self.workflow_service = WorkflowService(session)
        self.insurance_service = InsuranceService(session)

    async def execute(
        self,
        *,
        command: AgentCommandInput,
        response: AgentStructuredResponse,
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        created_entities: list[CreatedEntity] = []
        policy: InsurancePolicy | None = None
        summary = result.summary or response.user_response or response.entities.get("summary")
        user_message = result.user_message or response.user_response or summary

        for action in response.proposed_actions:
            if action.tool_name == "create_policy":
                resolved = await self._resolve_policyholder(
                    organization_id=command.organization_id,
                    policyholder_name=action.args.get("policyholder_name"),
                    allow_create=True,
                )
                if isinstance(resolved, AgentExecutionResult):
                    return resolved
                contact, contact_created = resolved
                if contact_created:
                    created_entities.append(CreatedEntity(type="contact", id=str(contact.id)))
                policy = await self._create_policy(command=command, action_args=action.args, contact=contact)
                created_entities.append(CreatedEntity(type="insurance_policy", id=str(policy.id)))
            elif action.tool_name == "create_policy_renewal_workflow":
                if policy is None:
                    policy_lookup = await self._resolve_policy(
                        organization_id=command.organization_id,
                        policyholder_name=action.args.get("policyholder_name"),
                        policy_number=action.args.get("policy_number"),
                        active_only=True,
                    )
                    if isinstance(policy_lookup, AgentExecutionResult):
                        return policy_lookup
                    policy = policy_lookup
                policy_channels = resolve_policy_reminder_channels(getattr(policy, "preferred_channel", None))
                workflow_entities, workflow_summary = await self._create_policy_workflow(
                    command=command,
                    policy=policy,
                    preferred_channel=action.args.get("preferred_channel") or (policy_channels[0] if policy_channels else None),
                    assigned_agent_user_id=action.args.get("assigned_agent_user_id"),
                )
                created_entities.extend(workflow_entities)
                summary = workflow_summary
                user_message = workflow_summary
            elif action.tool_name == "mark_policy_renewed":
                resolved = await self._resolve_policy(
                    organization_id=command.organization_id,
                    policyholder_name=action.args.get("policyholder_name"),
                    policy_number=action.args.get("policy_number"),
                    active_only=True,
                )
                if isinstance(resolved, AgentExecutionResult):
                    return resolved
                policy = resolved
                await self._mark_policy_renewed(policy=policy, actor_user_id=command.actor_user_id)
                created_entities.append(CreatedEntity(type="insurance_policy", id=str(policy.id)))
                summary = f"Marked policy {policy.policy_number} as renewed and canceled remaining reminders."
                user_message = summary
            elif action.tool_name == "create_lead_followup" or action.tool_name == "log_demo":
                lead = await self.insurance_service.create_lead(
                    organization_id=command.organization_id,
                    contact_name=action.args.get("policyholder_name"),
                    actor_user_id=command.actor_user_id,
                    assigned_agent_user_id=action.args.get("assigned_agent_user_id") or command.actor_user_id,
                    source="demo",
                    notes=action.args.get("notes"),
                    demo_logged_at=utcnow_naive(),
                    followup_due_at=self._parse_datetime(action.args.get("followup_at")),
                )
                workflow_result = await self.insurance_service.start_lead_followup_workflow(
                    lead_id=lead.id,
                    actor_user_id=command.actor_user_id,
                    followup_due_at=self._parse_datetime(action.args.get("followup_at")),
                )
                created_entities.extend(
                    [
                        CreatedEntity(type="insurance_lead", id=str(lead.id)),
                        CreatedEntity(type="workflow_template", id=str(workflow_result["workflow_template"].id)),
                        CreatedEntity(type="workflow_run", id=str(workflow_result["workflow_run"].id)),
                        CreatedEntity(type="task", id=str(workflow_result["task"].id)),
                        CreatedEntity(type="reminder", id=str(workflow_result["reminder"].id)),
                    ]
                )
                summary = f"Created a demo follow-up for lead {lead.id}."
                user_message = summary
            elif action.tool_name == "summarize_renewals":
                policies = await self._list_upcoming_policies(command.organization_id)
                summary = self._summarize_renewals(policies)
                user_message = summary
            elif action.tool_name == "mark_lead_not_interested":
                try:
                    lead = await self.insurance_service.find_open_lead(
                        organization_id=command.organization_id,
                        contact_name=action.args.get("policyholder_name") or action.args.get("contact_name"),
                    )
                except ValueError as exc:
                    return self._clarification(str(exc), ["lead"])
                await self.insurance_service.update_lead(
                    lead.id,
                    {"status": "not_interested"},
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="insurance_lead", id=str(lead.id)))
                summary = "Marked the lead as not interested."
                user_message = summary
            elif action.tool_name == "reschedule_followup":
                try:
                    lead = await self.insurance_service.find_open_lead(
                        organization_id=command.organization_id,
                        contact_name=action.args.get("policyholder_name") or action.args.get("contact_name"),
                    )
                except ValueError as exc:
                    return self._clarification(str(exc), ["lead"])
                followup_at = self._parse_datetime(action.args.get("followup_at"))
                if followup_at is None:
                    return self._clarification("When should I reschedule this follow-up?", ["followup_at"])
                await self.insurance_service.update_lead(
                    lead.id,
                    {"status": "follow_up_later", "followup_due_at": followup_at},
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="insurance_lead", id=str(lead.id)))
                summary = "Rescheduled the lead follow-up."
                user_message = summary
            elif action.tool_name == "create_premium_reminder":
                resolved = await self._resolve_policy(
                    organization_id=command.organization_id,
                    policyholder_name=action.args.get("policyholder_name"),
                    policy_number=action.args.get("policy_number"),
                    active_only=True,
                )
                if isinstance(resolved, AgentExecutionResult):
                    return resolved
                policy = resolved
                policy_channels = resolve_policy_reminder_channels(getattr(policy, "preferred_channel", None))
                if not (action.args.get("preferred_channel") or policy_channels):
                    return self._clarification("What channel should I use for this premium reminder?", ["preferred_channel"])
                task = await self.task_service.create_task(
                    organization_id=command.organization_id,
                    title=f"Premium reminder for {policy.policy_number}",
                    description=None,
                    due_at=self._parse_datetime(action.args.get("scheduled_for")),
                    domain="insurance",
                    actor_user_id=command.actor_user_id,
                )
                reminder = await self.reminder_service.create_reminder(
                    organization_id=command.organization_id,
                    task_id=task.id,
                    dedupe_key=self._dedupe_key(command, f"premium-{policy.id}"),
                    scheduled_for=self._parse_datetime(action.args.get("scheduled_for")),
                    actor_user_id=command.actor_user_id,
                )
                created_entities.extend([
                    CreatedEntity(type="task", id=str(task.id)),
                    CreatedEntity(type="reminder", id=str(reminder.id)),
                ])
                summary = f"Created a premium reminder for {policy.policyholder_id}."
                user_message = summary

        return result.model_copy(
            update={
                "created_entities": created_entities,
                "summary": summary,
                "user_message": user_message,
            }
        )

    async def _create_policy(
        self,
        *,
        command: AgentCommandInput,
        action_args: dict,
        contact: Contact,
    ) -> InsurancePolicy:
        now = utcnow_naive()
        policy_number = action_args.get("policy_number") or self._generate_policy_number(command, contact.name)
        existing = await self.session.execute(
            select(InsurancePolicy).where(InsurancePolicy.policy_number == policy_number)
        )
        if existing.scalar_one_or_none() is not None:
            policy_number = f"{policy_number}-{sha1(str(now).encode('utf-8')).hexdigest()[:4]}"
        # Use PolicyService to ensure canonical premium conversion and behavior
        svc = PolicyService(self.session)
        premium_val = action_args.get("premium_amount")
        premium_decimal = None
        if premium_val is not None:
            # assume premium_amount provided in whole units; do not divide by 100
            try:
                premium_decimal = Decimal(premium_val)
            except Exception:
                premium_decimal = Decimal(premium_val)
        policy = await svc.create_policy(
            organization_id=command.organization_id,
            policyholder_name=contact.name,
            policy_number=policy_number,
            expiry_date=self._parse_datetime(action_args.get("expiry_date")),
            premium=premium_decimal,
            policy_type=action_args.get("policy_type"),
            carrier=action_args.get("carrier"),
            assigned_agent_id=action_args.get("assigned_agent_user_id") or command.actor_user_id,
            preferred_channel=action_args.get("preferred_channel"),
            actor_user_id=command.actor_user_id,
        )
        return policy

    async def _create_policy_workflow(
        self,
        *,
        command: AgentCommandInput,
        policy: InsurancePolicy,
        preferred_channel: str | None,
        assigned_agent_user_id: int | None,
    ) -> tuple[list[CreatedEntity], str]:
        if policy.expiry_date is None:
            return [], ""
        if not preferred_channel:
            return [], ""

        template = await self._ensure_workflow_template(command.organization_id)
        root_task = await self.task_service.create_task(
            organization_id=command.organization_id,
            title=f"Policy renewal for {policy.policy_number}",
            description=f"Renewal workflow for policyholder {policy.policyholder_id}",
            due_at=policy.expiry_date + timedelta(days=1),
            domain="insurance",
            actor_user_id=command.actor_user_id,
        )
        run = await self.workflow_service.start_workflow_run(
            organization_id=command.organization_id,
            workflow_template_id=template.id,
            task_id=root_task.id,
            current_step="scheduled",
            actor_user_id=command.actor_user_id,
        )
        await self.workflow_service.advance_workflow_state(
            run.id,
            current_step="scheduled",
            state_payload=json.dumps({"policy_id": policy.id, "task_id": root_task.id, "preferred_channel": preferred_channel}),
            actor_user_id=command.actor_user_id,
        )

        entities = [
            CreatedEntity(type="workflow_template", id=str(template.id)),
            CreatedEntity(type="task", id=str(root_task.id)),
            CreatedEntity(type="workflow_run", id=str(run.id)),
        ]

        summary = f"Created policy {policy.policy_number} and renewal workflow for {policy.policyholder_id}."
        return entities, summary

    async def _create_demo_followup(
        self,
        *,
        command: AgentCommandInput,
        contact: Contact,
        followup_at: datetime | None,
        assigned_agent_user_id: int | None,
    ) -> tuple[list[CreatedEntity], str]:
        followup_at = followup_at or (utcnow_naive() + timedelta(days=3))
        task = await self.task_service.create_task(
            organization_id=command.organization_id,
            title=f"Demo follow-up with {contact.name}",
            description=None,
            due_at=followup_at,
            domain="insurance",
            actor_user_id=command.actor_user_id,
        )
        reminder = await self.reminder_service.create_reminder(
            organization_id=command.organization_id,
            task_id=task.id,
            dedupe_key=self._dedupe_key(command, f"demo-{contact.id}"),
            scheduled_for=followup_at,
            actor_user_id=assigned_agent_user_id or command.actor_user_id,
        )
        return [
            CreatedEntity(type="task", id=str(task.id)),
            CreatedEntity(type="reminder", id=str(reminder.id)),
        ], f"Created a demo follow-up for {contact.name}."

    async def _mark_policy_renewed(self, *, policy: InsurancePolicy, actor_user_id: int | None) -> None:
        await self.insurance_service.mark_policy_renewed(
            policy_id=policy.id,
            actor_user_id=actor_user_id,
        )

    async def _resolve_policyholder(
        self,
        *,
        organization_id: int,
        policyholder_name: str | None,
        allow_create: bool,
    ) -> tuple[Contact, bool] | AgentExecutionResult:
        if not policyholder_name or policyholder_name.lower() == "unknown":
            return self._clarification("Please provide contact details for the policyholder.", ["policyholder"])
        result = await self.session.execute(
            select(Contact).where(
                Contact.organization_id == organization_id,
                Contact.name.ilike(f"%{policyholder_name}%"),
            )
        )
        contacts = list(result.scalars())
        if len(contacts) > 1:
            return self._clarification(
                f"I found multiple contacts matching {policyholder_name}. Please specify the exact contact.",
                ["policyholder"],
            )
        if contacts:
            return contacts[0], False
        if not allow_create:
            return self._clarification("Please provide contact details for the policyholder.", ["policyholder"])
        now = utcnow_naive()
        contact = Contact(
            organization_id=organization_id,
            name=policyholder_name,
            email=None,
            phone=None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(contact)
        await self.session.commit()
        await self.session.refresh(contact)
        return contact, True

    async def _resolve_policy(
        self,
        *,
        organization_id: int,
        policyholder_name: str | None,
        policy_number: str | None,
        active_only: bool,
    ) -> InsurancePolicy | AgentExecutionResult:
        query = select(InsurancePolicy).where(InsurancePolicy.organization_id == organization_id)
        if active_only:
            query = query.where(InsurancePolicy.status == "active")
        if policy_number:
            query = query.where(InsurancePolicy.policy_number == policy_number)
        elif policyholder_name:
            contact_result = await self.session.execute(
                select(Contact).where(
                    Contact.organization_id == organization_id,
                    Contact.name.ilike(f"%{policyholder_name}%"),
                )
            )
            contacts = list(contact_result.scalars())
            if not contacts:
                return self._clarification("Please provide contact details for the policyholder.", ["policyholder"])
            contact_ids = [contact.id for contact in contacts]
            query = query.where(InsurancePolicy.policyholder_id.in_(contact_ids))
        else:
            return self._clarification("Which policy should I use?", ["policy"])
        result = await self.session.execute(query)
        policies = list(result.scalars())
        if not policies:
            return self._clarification("I could not find a matching policy.", ["policy"])
        if len(policies) > 1:
            return self._clarification("I found multiple matching policies. Which policy should I use?", ["policy"])
        return policies[0]

    async def _ensure_workflow_template(self, organization_id: int) -> WorkflowTemplate:
        result = await self.session.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.organization_id == organization_id,
                WorkflowTemplate.name == "policy_renewal_workflow",
                WorkflowTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if template is not None:
            return template
        return await self.workflow_service.create_workflow_template(
            organization_id=organization_id,
            name="policy_renewal_workflow",
            definition="expiry -10,-5,-2,0,+1",
        )

    async def _list_upcoming_policies(self, organization_id: int) -> list[InsurancePolicy]:
        result = await self.session.execute(
            select(InsurancePolicy).where(
                InsurancePolicy.organization_id == organization_id,
                InsurancePolicy.status == "active",
            )
        )
        return list(result.scalars())

    def _summarize_renewals(self, policies: list[InsurancePolicy]) -> str:
        if not policies:
            return "Renewal summary: no active policies."
        rendered = ", ".join(f"{policy.policy_number} expiring {policy.expiry_date.date().isoformat()}" for policy in policies)
        return f"Renewal summary: {rendered}"

    def _generate_policy_number(self, command: AgentCommandInput, policyholder_name: str) -> str:
        digest = sha1(f"{command.organization_id}:{command.command_text}:{policyholder_name}".encode("utf-8")).hexdigest()[:8].upper()
        return f"POL-{digest}"

    def _dedupe_key(self, command: AgentCommandInput, seed: str) -> str:
        digest = sha1(f"{command.organization_id}:{command.command_text}:{seed}".encode("utf-8")).hexdigest()[:12]
        return f"insurance-{digest}"

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            dt = datetime.fromisoformat(value)
        except Exception:
            return None
        # normalize to timezone-naive UTC for storage/comparisons
        from app.utils.datetime_utils import normalize_to_utc_naive

        return normalize_to_utc_naive(dt)

    def _clarification(self, question: str, missing_fields: list[str]) -> AgentExecutionResult:
        return AgentExecutionResult(
            status="needs_clarification",
            agent_key="insurance_agent",
            domain="insurance",
            intent="follow_up",
            confidence=0.5,
            summary=None,
            created_entities=[],
            missing_fields=missing_fields,
            approval_request_id=None,
            user_message=None,
            structured_response=None,
            clarification=ClarificationRequest(question=question, missing_fields=missing_fields),
            approval_required=None,
        )
