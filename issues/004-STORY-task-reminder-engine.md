---
title: "[ATM-004] [Story] Core Task, Workflow, and Reminder Engine"
labels: [story, backend, reminders, celery, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-004 - Core Task, Workflow, and Reminder Engine

## Objective

Build generic task CRUD, assignment, workflow, reminder scheduling, reminder processing, acknowledgement, snooze, cancellation, and escalation support.

## Implementation Steps

1. Implement task services:
   - create task
   - update task
   - assign task
   - complete task
   - cancel task
   - snooze task
   - list/filter tasks

2. Implement reminder services:
   - create reminder
   - cancel reminder
   - acknowledge reminder
   - snooze reminder
   - list pending reminders
   - find due reminders

3. Implement workflow services:
   - create workflow template
   - start workflow run
   - advance workflow state
   - complete workflow
   - cancel workflow

4. Implement Celery jobs:
   - `process_due_reminders`
   - `retry_failed_reminder_attempts`
   - `escalate_overdue_tasks`

5. Implement idempotency:
   - reminder `dedupe_key`
   - outbound message provider ID tracking
   - job locks or transaction-safe status transitions

6. Implement audit events for every state change.

7. Add APIs:
   - `POST /api/v1/tasks`
   - `GET /api/v1/tasks`
   - `PATCH /api/v1/tasks/{task_id}`
   - `POST /api/v1/tasks/{task_id}/complete`
   - `POST /api/v1/tasks/{task_id}/snooze`
   - `POST /api/v1/reminders`
   - `POST /api/v1/reminders/{reminder_id}/ack`

## Acceptance Criteria

- [ ] Users can create, assign, complete, and snooze tasks.
- [ ] Reminders are processed only once.
- [ ] Failed reminders create attempts and can be retried.
- [ ] Completed tasks cancel remaining reminders when configured.
- [ ] Every state change creates an audit event.

## Test Cases

- Creating a task creates audit event.
- Assigning a task validates assignee belongs to tenant.
- Processing due reminder sends outbound message through mock channel adapter.
- Duplicate Celery run does not send duplicate reminder.
- Snoozing reminder updates scheduled time.
- Completing task cancels future reminders.

## Validation

```bash
cd backend
python -m pytest tests/unit/services/test_task_service.py -v
python -m pytest tests/unit/services/test_reminder_service.py -v
python -m pytest tests/integration/test_reminder_processor.py -v
```

