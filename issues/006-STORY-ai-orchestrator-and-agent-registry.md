---
title: "[ATM-006] [Story] AI Orchestrator and Specialized Agent Registry"
labels: [story, backend, ai, agents, guardrails, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-006 - AI Orchestrator and Specialized Agent Registry

## Objective

Implement the AI orchestration layer that classifies user intent, routes work to specialized agents, validates structured output, enforces guardrails, and executes approved tools.

## Implementation Steps

1. Create agent registry:
   - General Task Agent
   - Insurance Agent
   - Construction Agent
   - Doctors Office Agent

2. Create orchestrator service:
   - normalize command input
   - load tenant/actor context
   - classify domain and intent
   - select agent
   - call LLM provider with tool policy
   - parse structured response
   - validate confidence and required fields
   - execute tools when allowed
   - create `agent_invocations`

3. Create tool layer:
   - `create_task`
   - `assign_task`
   - `create_reminder`
   - `start_workflow`
   - `send_message`
   - `create_contact`
   - `create_insurance_policy`
   - `create_insurance_lead`
   - `create_construction_project`
   - `create_construction_site`
   - `create_medical_office_task`

4. Add guardrail service:
   - tenant scope checks
   - role permission checks
   - sensitivity detection
   - customer consent check
   - human approval requirement
   - prompt-injection logging

5. Add API:
   - `POST /api/v1/ai/command`
   - `POST /api/v1/ai/classify`
   - `GET /api/v1/agents`
   - `GET /api/v1/agent-invocations`

6. Add deterministic test mode:
   - fake LLM provider
   - fixture-based agent outputs
   - no external model calls in unit/integration tests

## Acceptance Criteria

- [ ] Commands route to correct specialized agent.
- [ ] Low-confidence commands ask for clarification.
- [ ] Sensitive actions require approval.
- [ ] Tools cannot bypass permissions.
- [ ] Agent invocations are stored with summaries, status, guardrail result, and tool calls.

## Test Cases

- "Renew policy for Ravi" routes to Insurance Agent.
- "Assign wiring to Kumar at Site A" routes to Construction Agent.
- "Verify insurance for patient appointment" routes to Doctors Office Agent and marks `phi_possible`.
- Cross-tenant tool input is rejected.
- Bulk external message requires human approval.
- Prompt injection text does not override tool policy.

## Validation

```bash
cd backend
python -m pytest tests/unit/ai/test_orchestrator.py -v
python -m pytest tests/unit/ai/test_agent_registry.py -v
python -m pytest tests/unit/ai/test_guardrails.py -v
python -m pytest tests/integration/test_ai_command_api.py -v
```

