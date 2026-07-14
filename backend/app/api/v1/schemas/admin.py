from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CustomerOut(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str


class OwnerUserOut(BaseModel):
    id: int
    email: str


class OnboardOut(BaseModel):
    owner_user: OwnerUserOut
    agents_enabled: bool
    workflows_configured: bool
    message_templates_configured: bool
    sample_workflow_run: bool


class HealthUsageOut(BaseModel):
    health_score: int
    active_users: int
    agent_invocations: int


class UsageOut(BaseModel):
    monthly_requests: int
    storage_used: str


class AuditLogOut(BaseModel):
    id: int
    organization_id: int
    event_type: str
    entity_type: str
    entity_id: str
    payload: Any
    created_at: str


class ReminderAttemptOut(BaseModel):
    id: int
    organization_id: int
    reminder_id: int
    attempt_number: int
    status: str
    error_message: Optional[str]
    next_retry_at: Optional[str]
    created_at: str


class AgentInvocationOut(BaseModel):
    id: int
    organization_id: int
    actor_user_id: Optional[int]
    agent: str
    domain: str
    intent: str
    confidence: float
    input_summary: str
    output_summary: str
    created_at: str


class SupportAccessOut(BaseModel):
    id: int
    organization_id: int
    created_by_user_id: Optional[int]
    started_at: Optional[str]
    ended_at: Optional[str]
    created_at: str
