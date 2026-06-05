---
title: "[ATM-012] [Task] Agent Contracts, Tenant Router, and Scoped Classifier"
labels: [task, backend, ai, agents, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-012 - Agent Contracts, Tenant Router, and Scoped Classifier

## Objective

Implement the shared foundation used by all specialized agents: typed contracts, registry, tenant-scoped agent routing, scoped domain classifier, fake LLM provider, structured output validation, and persisted agent invocation records.

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
   - expose enabled agents from `organization_agent_configs` by tenant/domain

3. Implement tenant agent router:
   - resolve tenant from authenticated request or verified channel connection
   - load tenant-enabled agents
   - select tenant primary agent when exactly one specialized agent is enabled
   - allow General Task Agent only when enabled for the tenant
   - never route to a disabled specialized agent based only on message text

4. Implement scoped domain classifier:
   - rule-based first pass using domain keywords within enabled agents only
   - LLM fallback only when enabled-agent confidence is ambiguous
   - confidence score
   - ambiguous enabled-domain clarification output
   - disabled-domain clarification/rejection output

5. Implement fake LLM provider:
   - deterministic fixture responses
   - no network calls in tests
   - used by orchestrator tests

6. Implement structured output validator:
   - required top-level fields
   - valid domain and intent
   - selected agent is enabled for tenant
   - valid proposed tool names
   - missing field handling
   - approval-required handling

7. Persist `agent_invocations`:
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

- [ ] Tenant router chooses the tenant primary specialized agent for single-agent tenants.
- [ ] Scoped classifier chooses only among agents enabled for the tenant.
- [ ] Commands never route to a disabled specialized agent based only on WhatsApp, Telegram, or web message text.
- [ ] Ambiguous command returns a clarification instead of executing.
- [ ] Agent registry exposes all four initial agents.
- [ ] Invalid structured output is rejected.
- [ ] Fake LLM provider allows deterministic tests.
- [ ] Agent invocations are persisted.

## Test Cases

- Insurance tenant with primary `insurance_agent`: "Create policy renewal for Ravi" routes to `insurance_agent`.
- Construction tenant with primary `construction_agent`: "Assign wiring at Site A to Kumar" routes to `construction_agent`.
- Medical-office tenant with primary `doctors_office_agent`: "Verify patient insurance for tomorrow" routes to `doctors_office_agent`.
- Insurance tenant mentioning "appointment" does not route to `doctors_office_agent` unless that agent is enabled for the tenant.
- Tenant with General Task Agent enabled: "Remind me to call Sam" routes to `general_task_agent` when no specialized workflow is needed.
- Multi-agent tenant with insurance and construction enabled classifies only between those enabled agents.
- Invalid tool name in agent response is rejected.

## Validation

```bash
cd backend
python -m pytest tests/unit/ai/test_agent_contracts.py -v
python -m pytest tests/unit/ai/test_agent_registry.py -v
python -m pytest tests/unit/ai/test_tenant_agent_router.py -v
python -m pytest tests/unit/ai/test_domain_classifier.py -v
python -m pytest tests/integration/test_agent_invocations.py -v
```
