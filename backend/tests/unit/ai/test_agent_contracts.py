import pytest

from app.ai.validator import StructuredOutputValidator


def valid_payload() -> dict:
    return {
        "domain": "insurance",
        "intent": "create_lead_followup",
        "confidence": 0.93,
        "summary": "Create policy renewal follow-up",
        "entities": {"policyholder_name": "Ravi", "summary": "Create policy renewal follow-up"},
        "proposed_actions": [
            {
                "tool_name": "create_lead_followup",
                "args": {"policyholder_name": "Ravi", "followup_at": "2099-06-25T09:00:00"},
            }
        ],
        "missing_fields": [],
        "requires_human_approval": False,
        "clarifying_question": None,
        "user_response": "Create policy renewal follow-up",
    }


def test_invalid_tool_name_is_rejected():
    validator = StructuredOutputValidator()
    payload = valid_payload()
    payload["proposed_actions"][0]["tool_name"] = "drop_database"

    with pytest.raises(ValueError, match="invalid proposed tool"):
        validator.validate(payload)


def test_missing_required_fields_are_rejected():
    validator = StructuredOutputValidator()
    payload = valid_payload()
    payload.pop("intent")

    with pytest.raises(ValueError, match="missing required fields"):
        validator.validate(payload)


def test_approval_required_handling_returns_approval_result():
    validator = StructuredOutputValidator()
    payload = valid_payload()
    payload["requires_human_approval"] = True
    parsed = validator.validate(payload)

    result = validator.to_execution_result(agent_key="insurance_agent", response=parsed)

    assert result.status == "needs_approval"
    assert result.approval_required is not None
    assert len(result.approval_required.proposed_actions) == 1
