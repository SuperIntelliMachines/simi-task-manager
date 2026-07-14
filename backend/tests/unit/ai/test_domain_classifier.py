from app.ai.domain_classifier import DomainClassifier
from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.registry import AgentRegistry


def test_policy_renewal_routes_to_insurance_agent():
    classifier = DomainClassifier(FakeLLMProvider())
    registry = AgentRegistry()

    result = classifier.classify("Create policy renewal for Ravi")
    agent = registry.resolve_agent_for_domain(result.domain or "general")

    assert result.domain == "insurance"
    assert agent == "insurance_agent"


def test_wiring_routes_to_construction_agent():
    classifier = DomainClassifier(FakeLLMProvider())
    registry = AgentRegistry()

    result = classifier.classify("Assign wiring at Site A to Kumar")
    agent = registry.resolve_agent_for_domain(result.domain or "general")

    assert result.domain == "construction"
    assert agent == "construction_agent"


def test_patient_insurance_routes_to_doctors_office_agent():
    classifier = DomainClassifier(FakeLLMProvider())
    registry = AgentRegistry()

    result = classifier.classify("Verify patient insurance for tomorrow")
    agent = registry.resolve_agent_for_domain(result.domain or "general")

    assert result.domain == "doctors_office"
    assert agent == "doctors_office_agent"


def test_reminder_routes_to_general_task_agent():
    classifier = DomainClassifier(FakeLLMProvider())
    registry = AgentRegistry()

    result = classifier.classify("Remind me to call Sam")
    agent = registry.resolve_agent_for_domain(result.domain or "general")

    assert result.domain == "general"
    assert agent == "general_task_agent"


def test_ambiguous_command_returns_clarification():
    classifier = DomainClassifier(FakeLLMProvider())

    result = classifier.classify("Follow up with Kumar")

    assert result.needs_clarification is True
    assert result.clarification is not None
