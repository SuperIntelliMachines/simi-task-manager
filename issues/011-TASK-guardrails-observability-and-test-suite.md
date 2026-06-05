---
title: "[ATM-011] [Task] Guardrails, Observability, and Test Suite"
labels: [task, backend, frontend, security, testing, observability, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-011 - Guardrails, Observability, and Test Suite

## Objective

Harden the platform with tenant isolation, RBAC, approval gates, privacy controls, audit history, channel safety, observability, and automated regression tests.

## Implementation Steps

1. Implement RBAC enforcement:
   - owner/admin configuration permissions
   - manager task reassignment permissions
   - staff own-task permissions
   - external contact response-only permissions
   - platform support audited access

2. Implement approval workflow:
   - approval requests table or generic task type
   - pending approval status
   - approve/reject APIs
   - UI states for approval-required AI actions

3. Implement privacy/safety checks:
   - consent required for first customer outbound message
   - WhatsApp STOP opt-out
   - quiet hours by recipient timezone
   - sensitive medical content approval
   - secret redaction in logs

4. Implement observability:
   - structured logs with tenant and request IDs
   - metrics for reminder sends, failures, retries, agent invocations, approvals
   - admin endpoint or dashboard for failed reminders
   - replay action for failed reminders with idempotency checks

5. Build regression test suite:
   - backend unit tests
   - backend integration tests
   - frontend component tests
   - frontend visual/UX regression checks for GyantrAI-aligned app shell, command bar, dashboard, drawer, loading, empty, and approval states
   - E2E smoke tests
   - mocked Telegram/WhatsApp/LLM providers

6. Add runbooks:
   - channel setup
   - failed reminder replay
   - webhook troubleshooting
   - tenant onboarding
   - production release checklist

## Acceptance Criteria

- [ ] Cross-tenant access is blocked in services and APIs.
- [ ] Sensitive AI actions require approval.
- [ ] External messaging respects consent and opt-out.
- [ ] Failed reminders are visible and replayable.
- [ ] Critical frontend states preserve the GyantrAI-aligned UX quality across desktop and mobile.
- [ ] No automated tests call real Telegram, WhatsApp, or LLM providers.
- [ ] Runbooks exist for operations.

## Test Cases

- Cross-tenant task ID returns 404 or forbidden.
- Staff cannot modify another user's task unless permission allows.
- Customer without consent cannot receive first outbound reminder.
- WhatsApp STOP cancels future external reminders.
- Sensitive medical outbound message requires approval.
- Failed reminder replay does not duplicate already-sent messages.
- Agent invocation logs guardrail decision.
- Approval-required UI, loading states, empty states, and admin replay confirmations render without layout breakage.

## Validation

```bash
cd backend
python -m pytest tests/ -v --cov=app --cov-report=term
ruff check app tests
mypy app

cd ../frontend
npm run typecheck
npm run test:coverage
npm run build
npm run test:e2e
```
