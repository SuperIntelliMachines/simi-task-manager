from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm012 import AgentDefinition



@dataclass(slots=True)
class RegisteredAgent:
    key: str
    name: str
    domain: str
    description: str
    system_prompt: str = ""
    tool_policy: dict = field(default_factory=dict)
    guardrail_policy: dict = field(default_factory=dict)
    status: str = "active"
    enabled: bool = True
    source: str = "builtin"
    config: dict = field(default_factory=dict)


class AgentRegistry:
    def __init__(self) -> None:
        self._builtin_agents: dict[str, RegisteredAgent] = {}
        self._persisted_agents_by_org: dict[int | None, dict[str, RegisteredAgent]] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        self.register_builtin(
            RegisteredAgent(
                key="general_task_agent",
                name="General Task Agent",
                domain="general",
                description="Handles generic reminders, assignments, and follow-ups.",
                system_prompt="Handle generic reminders, assignments, and follow-ups. Never perform vertical-specific actions.",
                tool_policy={"allowed_tools": ["create_task", "assign_task", "create_reminder", "complete_task", "snooze_task", "summarize_tasks", "list_overdue_tasks", "reschedule_task"]},
                guardrail_policy={"require_approval_for_bulk": True},
                status="active",
            )
        )
        self.register_builtin(
            RegisteredAgent(
                key="insurance_agent",
                name="Insurance Agent",
                domain="insurance",
                description="Handles policy, renewal, premium, and lead workflows.",
                system_prompt="Handle insurance workflows for policy renewals, premiums, leads, and demos.",
                tool_policy={"allowed_tools": ["create_policy", "create_policy_renewal_workflow", "create_premium_reminder", "log_demo", "create_lead_followup", "mark_policy_renewed", "mark_lead_not_interested", "reschedule_followup", "summarize_renewals", "summarize_agent_followups"]},
                guardrail_policy={"require_approval_for_bulk": True, "no_unverified_channel": True},
                status="active",
            )
        )
        self.register_builtin(
            RegisteredAgent(
                key="construction_agent",
                name="Construction Agent",
                domain="construction",
                description="Handles project, site, worker, and owner update workflows.",
                system_prompt="Handle construction project, site, worker, and owner update workflows.",
                tool_policy={"allowed_tools": ["create_project", "create_site", "assign_worker_task", "request_completion_update", "mark_task_done", "mark_task_blocked", "request_completion_photo", "create_owner_update", "summarize_site_progress", "summarize_worker_workload"]},
                guardrail_policy={"require_approval_for_owner_update": True},
                status="active",
            )
        )
        self.register_builtin(
            RegisteredAgent(
                key="doctors_office_agent",
                name="Doctors Office Agent",
                domain="doctors_office",
                description="Handles privacy-aware office tasks for appointments, insurance, and referrals.",
                system_prompt="Handle privacy-aware office tasks for appointments, insurance, and referrals. Never send PHI externally.",
                tool_policy={"allowed_tools": ["create_appointment_prep_task", "create_insurance_verification_task", "create_referral_followup_task", "create_billing_followup_task", "assign_staff_task", "summarize_office_tasks", "list_overdue_sensitive_tasks"]},
                guardrail_policy={"no_external_phi": True, "require_approval_for_external_patient": True},
                status="active",
            )
        )

    def register_builtin(self, agent: RegisteredAgent) -> None:
        self._builtin_agents[agent.key] = agent

    async def load_persisted_definitions(
        self,
        session: AsyncSession,
        organization_id: int | None = None,
    ) -> None:
        query = select(AgentDefinition)
        if organization_id is not None:
            query = query.where(
                (AgentDefinition.organization_id == organization_id)
                | (AgentDefinition.organization_id.is_(None))
            )
        result = await session.execute(query)
        rows = list(result.scalars())

        grouped: dict[int | None, dict[str, RegisteredAgent]] = {}
        for row in rows:
            org = row.organization_id
            grouped.setdefault(org, {})[row.key] = RegisteredAgent(
                key=row.key,
                name=row.name,
                domain=row.domain,
                description=row.description or "",
                system_prompt=row.system_prompt or "",
                tool_policy=row.tool_policy or {},
                guardrail_policy=row.guardrail_policy or {},
                status=row.status or "active",
                enabled=row.is_enabled,
                source="persisted",
                config=row.config or {},
            )

        for org, agents in grouped.items():
            self._persisted_agents_by_org[org] = agents

    def list_enabled_agents(
        self,
        organization_id: int | None = None,
        domain: str | None = None,
    ) -> list[RegisteredAgent]:
        merged = dict(self._builtin_agents)

        global_overrides = self._persisted_agents_by_org.get(None, {})
        merged.update(global_overrides)

        if organization_id is not None:
            tenant_overrides = self._persisted_agents_by_org.get(organization_id, {})
            merged.update(tenant_overrides)

        rows = [row for row in merged.values() if row.enabled and row.status == "active"]
        if domain is not None:
            rows = [row for row in rows if row.domain == domain]

        return rows

    def resolve_agent_for_domain(self, domain: str, organization_id: int | None = None) -> str:
        domain_agents = self.list_enabled_agents(organization_id=organization_id, domain=domain)
        if domain_agents:
            return domain_agents[0].key

        fallback = self.list_enabled_agents(organization_id=organization_id, domain="general")
        if fallback:
            return fallback[0].key

        raise ValueError("no enabled agents available")
