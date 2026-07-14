from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.validator import StructuredOutputValidator
from app.schemas.atm012 import AgentCommandInput


def test_general_reminder_extracts_task_and_time():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "general_task_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Remind me to call Suresh tomorrow morning",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "create_reminder"
    assert parsed.entities["title"] == "Call Suresh"
    assert parsed.entities["recipient"] == "Suresh"
    assert parsed.proposed_actions[0].tool_name == "create_reminder"


def test_assignment_without_due_date_requests_clarification():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "general_task_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Assign Priya to submit report",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "assign_task"
    assert parsed.missing_fields == ["due_date"]
    assert parsed.clarifying_question == "When is this task due?"


def test_assignment_without_assignee_requests_clarification():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "general_task_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Assign the report by Friday",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "assign_task"
    assert parsed.missing_fields == ["assignee"]
    assert parsed.clarifying_question == "Who should I assign this task to?"


def test_snooze_without_task_context_requests_clarification():
    provider = FakeLLMProvider()
    validator = StructuredOutputValidator()

    payload = provider.generate_structured_response(
        "general_task_agent",
        AgentCommandInput(
            organization_id=1,
            actor_user_id=None,
            command_text="Snooze this to Monday",
            context={},
        ),
    )
    parsed = validator.validate(payload)

    assert parsed.intent == "snooze_task"
    assert parsed.missing_fields == ["task"]
