---
title: "[ATM-015] [Story] Construction Specialized Agent"
labels: [story, backend, ai, agents, construction, P1]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-015 - Construction Specialized Agent

## Objective

Implement the Construction Agent that understands projects, sites, workers, work orders, completion proof, blocked tasks, and owner updates.

## Implementation Steps

1. Implement Construction Agent prompt and policy:
   - domain: `construction`
   - allowed tools: project, site, worker contact, task, reminder, attachment, owner update draft
   - owner external messages require approval

2. Implement intents:
   - `create_project`
   - `create_site`
   - `assign_worker_task`
   - `request_completion_update`
   - `mark_task_done`
   - `mark_task_blocked`
   - `request_completion_photo`
   - `create_owner_update`
   - `summarize_site_progress`
   - `summarize_worker_workload`

3. Implement entity extraction:
   - project
   - site
   - worker
   - work item
   - due date
   - manager
   - owner recipient
   - proof requirement

4. Implement workflow mapping:
   - worker assignment workflow
   - blocked task workflow
   - overdue escalation workflow
   - owner update approval workflow

5. Implement clarification handling:
   - unknown worker
   - unknown site
   - missing due date
   - ambiguous "owner"

6. Implement approval handling:
   - owner updates
   - bulk worker messages
   - messages containing internal cost or dispute data

## Acceptance Criteria

- [ ] Natural language can assign a worker task to a project/site.
- [ ] Worker task creates reminder on selected channel.
- [ ] Done reply completes task when target is clear.
- [ ] Blocked reply marks task waiting and asks for reason.
- [ ] Owner update is drafted but not sent until manager approval.
- [ ] Unknown worker/site triggers clarification.

## Test Cases

- "Assign Ravi to finish wiring at Site A by tomorrow" creates assigned construction task.
- "Ask Site B workers for status" creates approval-required bulk action.
- "Done" from worker completes active task when only one active task exists.
- "Blocked because material missing" marks waiting and records reason.
- "Update owner on Project Phoenix" creates approval request with draft.
- Owner update with cost dispute details is blocked for review.

## Validation

```bash
cd backend
python -m pytest tests/unit/agents/test_construction_agent.py -v
python -m pytest tests/integration/test_construction_agent_command_flow.py -v
```

