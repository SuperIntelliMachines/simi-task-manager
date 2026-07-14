from pydantic import ValidationError

from app.schemas.atm012 import (
    AgentExecutionResult,
    AgentStructuredResponse,
    ApprovalRequiredResult,
    ClarificationRequest,
    VALID_DOMAINS,
    VALID_INTENTS,
)


class StructuredOutputValidator:
    def __init__(self, allowed_tool_names: set[str] | None = None):
        self.allowed_tool_names = allowed_tool_names or {
            "create_task",
            "assign_task",
            "create_reminder",
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
            "verify_patient_insurance",
            "request_approval",
        }
        self.required_fields = {
            "domain",
            "intent",
            "confidence",
            "summary",
            "proposed_actions",
        }

    def validate(self, payload: dict) -> AgentStructuredResponse:
        missing = [field for field in self.required_fields if field not in payload]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")

        try:
            parsed = AgentStructuredResponse.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"invalid structured output: {exc}") from exc

        if parsed.domain not in VALID_DOMAINS:
            raise ValueError(f"invalid domain: {parsed.domain}")

        if parsed.intent not in VALID_INTENTS:
            raise ValueError(f"invalid intent: {parsed.intent}")

        for action in parsed.proposed_actions:
            if action.tool_name not in self.allowed_tool_names:
                raise ValueError(f"invalid proposed tool: {action.tool_name}")

        return parsed

    def to_execution_result(
        self,
        *,
        agent_key: str,
        response: AgentStructuredResponse,
    ) -> AgentExecutionResult:
        # Clarification needed
        if response.missing_fields:
            return AgentExecutionResult(
                status="needs_clarification",
                agent_key=agent_key,
                domain=response.domain,
                intent=response.intent,
                confidence=response.confidence,
                summary=None,
                created_entities=[],
                missing_fields=response.missing_fields,
                approval_request_id=None,
                user_message=None,
                structured_response=response,
                clarification=ClarificationRequest(
                    question=response.clarifying_question
                    or "Please provide missing details to continue.",
                    missing_fields=response.missing_fields,
                ),
                approval_required=None,
            )

        # Approval required
        if response.requires_human_approval:
            return AgentExecutionResult(
                status="needs_approval",
                agent_key=agent_key,
                domain=response.domain,
                intent=response.intent,
                confidence=response.confidence,
                summary=response.user_response or response.entities.get("summary"),
                created_entities=[],
                missing_fields=[],
                approval_request_id=None,
                user_message=response.user_response,
                structured_response=response,
                clarification=None,
                approval_required=ApprovalRequiredResult(
                    reason=response.approval_reason or "This action requires human approval before execution.",
                    proposed_actions=response.proposed_actions,
                ),
            )

        # Normal execution
        return AgentExecutionResult(
            status="executed",
            agent_key=agent_key,
            domain=response.domain,
            intent=response.intent,
            confidence=response.confidence,
            summary=response.user_response or response.entities.get("summary"),
            created_entities=[],
            missing_fields=[],
            approval_request_id=None,
            user_message=response.user_response,
            structured_response=response,
            clarification=None,
            approval_required=None,
        )
