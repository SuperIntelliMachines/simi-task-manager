---
title: "[ATM-008] [Story] Construction Agent MVP"
labels: [story, backend, frontend, construction, P1]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-008 - Construction Agent MVP

## Objective

Support construction customers who need project/site task assignment, worker reminders, completion updates, and owner/manager status reporting.

## Implementation Steps

1. Implement construction services:
   - project CRUD
   - site CRUD
   - worker contact setup
   - task creation with project/site context

2. Implement worker assignment workflow:
   - create task for worker
   - send reminder through worker preferred channel
   - capture done/blocked replies
   - allow completion proof attachment metadata
   - escalate overdue task to manager

3. Implement owner update workflow:
   - create summary from completed tasks
   - require manager approval before external owner message
   - send through owner preferred channel

4. Extend Construction Agent:
   - extract worker, project, site, due date, work item
   - create task and reminder from natural language
   - detect blocked status and ask for reason

5. Add APIs:
   - `POST /api/v1/construction/projects`
   - `GET /api/v1/construction/projects`
   - `POST /api/v1/construction/sites`
   - `GET /api/v1/construction/sites`
   - `POST /api/v1/construction/tasks/from-command`
   - `GET /api/v1/construction/dashboard`

## Acceptance Criteria

- [ ] Manager can create project and site.
- [ ] Manager can assign worker task with due date.
- [ ] Worker receives Telegram or WhatsApp reminder.
- [ ] Worker can reply done or blocked.
- [ ] Overdue worker task escalates to manager.
- [ ] Owner update requires approval before sending.

## Test Cases

- Natural language command creates construction task with project/site metadata.
- Unknown worker triggers clarification instead of creating task.
- Worker reply "done" marks task completed.
- Worker reply "blocked" marks task waiting and asks reason.
- Overdue task creates escalation.
- Owner message is blocked until manager approval.

## Validation

```bash
cd backend
python -m pytest tests/unit/construction/test_worker_task_workflow.py -v
python -m pytest tests/unit/construction/test_owner_update_guardrail.py -v
python -m pytest tests/integration/test_construction_api.py -v
```

