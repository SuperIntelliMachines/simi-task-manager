from datetime import UTC, datetime, timedelta

from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.validator import StructuredOutputValidator
from app.schemas.atm012 import AgentCommandInput


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_create_policy_extracts_workflow_actions():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "insurance_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Create auto policy for Ravi expiring June 25 2099 and remind him on WhatsApp",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "create_policy_renewal_workflow"
    assert parsed.entities["policyholder_name"] == "Ravi"
    assert parsed.entities["preferred_channel"] == "whatsapp"
    assert [action.tool_name for action in parsed.proposed_actions] == [
        "create_policy",
        "create_policy_renewal_workflow",
    ]


def test_missing_expiry_requests_clarification():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "insurance_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Create auto policy for Ravi and remind him on WhatsApp",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "create_policy_renewal_workflow"
    assert "expiry_date" in parsed.missing_fields
    assert parsed.clarifying_question == "When does this policy expire?"


def test_bulk_renewal_campaign_requires_approval():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "insurance_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Send renewal reminders to all expiring customers",
            context={},
        ),
    )
    parsed = validator.validate(payload)
    result = validator.to_execution_result(agent_key="insurance_agent", response=parsed)

    assert parsed.requires_human_approval is True
    assert result.status == "needs_approval"
    assert result.approval_required is not None
    assert result.approval_required.reason == "Bulk customer reminders require approval."


def test_demo_followup_creates_followup_action():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "insurance_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Follow up with Priya after demo in 3 days",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "create_lead_followup"
    assert parsed.entities["policyholder_name"] == "Priya"
    followup_at = datetime.fromisoformat(parsed.entities["followup_at"])
    assert followup_at >= utcnow_naive() + timedelta(days=2)
    assert parsed.proposed_actions[0].tool_name == "create_lead_followup"
