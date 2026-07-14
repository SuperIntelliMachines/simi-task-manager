from app.services.insurance_service import build_agent_follow_up_message


def test_build_agent_follow_up_message():
    message = build_agent_follow_up_message(
        customer_name="Priya Sharma",
        policy_type="health",
    )
    assert "Follow up with Priya Sharma" in message
    assert "regarding the health policy decision." in message


def test_build_agent_follow_up_message_defaults_policy_type():
    message = build_agent_follow_up_message(customer_name="Ravi", policy_type=None)
    assert "regarding the insurance policy decision." in message
