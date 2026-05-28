---
title: "[ATM-017] [Task] Approval, Agent Sessions, Message Templates, and Notification Preferences"
labels: [task, backend, database, guardrails, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-017 - Approval, Agent Sessions, Message Templates, and Notification Preferences

## Objective

Add the final hardening layer required before development: first-class approval requests, agent session context, approved message templates, and recipient notification preferences.

## Reference

Read:

- `docs/agentic-task-manager-platform-spec.md`
- `docs/specialized-agents-implementation.md`

## Implementation Steps

1. Add database models and migrations:
   - `approval_requests`
   - `agent_sessions`
   - `message_templates`
   - `notification_preferences`

2. Implement approval service:
   - create approval request
   - approve request
   - reject request
   - expire old requests
   - execute approved proposed actions safely
   - write audit events

3. Implement agent session service:
   - create clarification session
   - store collected fields
   - resume session on user reply
   - expire stale sessions
   - link sessions to agent invocations

4. Implement message template service:
   - CRUD templates
   - approve/archive templates
   - validate required variables
   - render preview with sample data
   - map WhatsApp provider template names

5. Implement notification preference service:
   - set preferred channel by purpose
   - enforce opt-out
   - enforce quiet hours
   - choose fallback channel
   - support contact and user preferences

6. Add APIs:
   - `GET /api/v1/approval-requests`
   - `POST /api/v1/approval-requests/{id}/approve`
   - `POST /api/v1/approval-requests/{id}/reject`
   - `GET /api/v1/agent-sessions/{id}`
   - `POST /api/v1/agent-sessions/{id}/reply`
   - `GET /api/v1/message-templates`
   - `POST /api/v1/message-templates`
   - `PATCH /api/v1/message-templates/{id}`
   - `POST /api/v1/message-templates/{id}/approve`
   - `GET /api/v1/notification-preferences`
   - `PUT /api/v1/notification-preferences/{id}`

## Acceptance Criteria

- [ ] Sensitive and bulk AI actions can be stored as approval requests.
- [ ] Approved requests execute exactly once.
- [ ] Rejected requests do not execute proposed actions.
- [ ] Clarification sessions preserve extracted fields and resume correctly.
- [ ] Message templates can be drafted, approved, archived, and rendered.
- [ ] Notification preferences are checked before outbound reminders.
- [ ] Quiet hours and opt-out are enforced.

## Test Cases

- Bulk insurance reminder returns approval request instead of sending.
- Approving the request creates outbound messages and audit events.
- Re-approving an approved request does not duplicate messages.
- Clarification for missing expiry date resumes policy creation after user reply.
- WhatsApp template render fails if required variable is missing.
- Contact opt-out prevents external reminder.
- Quiet hours delays non-urgent reminder.

## Validation

```bash
cd backend
python -m pytest tests/unit/services/test_approval_service.py -v
python -m pytest tests/unit/services/test_agent_session_service.py -v
python -m pytest tests/unit/services/test_message_template_service.py -v
python -m pytest tests/unit/services/test_notification_preferences.py -v
python -m pytest tests/integration/test_approval_and_clarification_flow.py -v
```

