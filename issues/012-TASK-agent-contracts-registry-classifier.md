---
title: "[ATM-012] [Task] Agent Contracts, Registry, and Domain Classifier"
labels: [task, backend, ai, agents, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-012 - Agent Contracts, Registry, and Domain Classifier

## Objective

Implement the shared foundation used by all specialized agents: typed contracts, registry, domain classifier, fake LLM provider, structured output validation, and persisted agent invocation records.

## Reference

Read `docs/specialized-agents-implementation.md`.

## Implementation Steps

1. Create agent schema models:
   - `AgentCommandInput`
   - `AgentStructuredResponse`
   - `AgentEntityExtraction`
   - `AgentProposedAction`
   - `AgentExecutionResult`
   - `ClarificationRequest`
   - `ApprovalRequiredResult`

2. Create agent registry:
   - register `general_task_agent`
   - register `insurance_agent`
   - register `construction_agent`
   - register `doctors_office_agent`
   - load persisted `agent_definitions`
   - expose enabled agents by tenant/domain

3. Implement domain classifier:
   - rule-based first pass using domain keywords
   - LLM fallback only when rule confidence is ambiguous
   - confidence score
   - ambiguous-domain clarification output

4. Implement fake LLM provider:
   - deterministic fixture responses
   - no network calls in tests
   - used by orchestrator tests

5. Implement structured output validator:
   - required top-level fields
   - valid domain and intent
   - valid proposed tool names
   - missing field handling
   - approval-required handling

6. Persist `agent_invocations`:
   - actor
   - agent
   - domain
   - intent
   - confidence
   - input summary
   - output summary
   - guardrail result
   - tool calls
   - token usage if available

## Acceptance Criteria

- [ ] Classifier routes commands to the correct specialized agent.
- [ ] Ambiguous command returns a clarification instead of executing.
- [ ] Agent registry exposes all four initial agents.
- [ ] Invalid structured output is rejected.
- [ ] Fake LLM provider allows deterministic tests.
- [ ] Agent invocations are persisted.

## Test Cases

- "Create policy renewal for Ravi" routes to `insurance_agent`.
- "Assign wiring at Site A to Kumar" routes to `construction_agent`.
- "Verify patient insurance for tomorrow" routes to `doctors_office_agent`.
- "Remind me to call Sam" routes to `general_task_agent`.
- "Follow up with Kumar" routes to general or asks clarification depending on context.
- Invalid tool name in agent response is rejected.

## Validation

```bash
cd backend
python -m pytest tests/unit/ai/test_agent_contracts.py -v
python -m pytest tests/unit/ai/test_agent_registry.py -v
python -m pytest tests/unit/ai/test_domain_classifier.py -v
python -m pytest tests/integration/test_agent_invocations.py -v
```

