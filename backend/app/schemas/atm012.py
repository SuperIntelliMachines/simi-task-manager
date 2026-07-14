from typing import Any

from pydantic import BaseModel, Field


VALID_DOMAINS = {"general", "insurance", "construction", "doctors_office"}
VALID_INTENTS = {
    "create_task",
    "create_reminder",
    "assign_task",
    "complete_task",
    "snooze_task",
    "summarize_tasks",
    "list_overdue_tasks",
    "create_policy",
    "create_policy_renewal_workflow",
    "create_premium_reminder",
    "log_demo",
    "create_lead_followup",
    "mark_policy_renewed",
    "mark_lead_not_interested",
    "reschedule_followup",
    "summarize_renewals",
    "policy_renewal",
    "verify_patient_insurance",
    "follow_up",
}


class AgentCommandInput(BaseModel):
    organization_id: int
    actor_user_id: int | None = None
    command_text: str
    context: dict[str, Any] = Field(default_factory=dict)


class AgentEntityExtraction(BaseModel):
    entity_type: str
    value: str
    confidence: float = 1.0


class AgentProposedAction(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None



class AgentStructuredResponse(BaseModel):
    domain: str
    intent: str
    confidence: float
    sensitivity: str = "normal"
    entities: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    proposed_actions: list[AgentProposedAction] = Field(default_factory=list)
    requires_human_approval: bool = False
    approval_reason: str | None = None
    clarifying_question: str | None = None
    user_response: str | None = None


class ClarificationRequest(BaseModel):
    question: str
    missing_fields: list[str] = Field(default_factory=list)


class ApprovalRequiredResult(BaseModel):
    reason: str
    proposed_actions: list[AgentProposedAction] = Field(default_factory=list)



class CreatedEntity(BaseModel):
    type: str
    id: str

class AgentExecutionResult(BaseModel):
    status: str  # executed|needs_clarification|needs_approval|rejected|failed
    domain: str
    intent: str
    agent_key: str
    confidence: float
    summary: str | None = None
    created_entities: list[CreatedEntity] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    approval_request_id: str | None = None
    user_message: str | None = None
    structured_response: AgentStructuredResponse | None = None
    clarification: ClarificationRequest | None = None
    approval_required: ApprovalRequiredResult | None = None


class DomainClassificationResult(BaseModel):
    domain: str | None
    confidence: float
    needs_clarification: bool = False
    clarification: ClarificationRequest | None = None
