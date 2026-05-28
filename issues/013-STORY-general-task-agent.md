---
title: "[ATM-013] [Story] General Task Agent"
labels: [story, backend, ai, agents, tasks, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-013 - General Task Agent

## Objective

Implement the fallback/general-purpose agent for normal task creation, assignment, reminders, snoozing, completion, and task summaries.

## Implementation Steps

1. Implement General Task Agent prompt and policy:
   - allowed domains: `general`
   - allowed tools: `create_task`, `assign_task`, `create_reminder`, `complete_task`, `snooze_task`, `summarize_tasks`
   - no external messages without consent checks

2. Implement intent handling:
   - `create_task`
   - `create_reminder`
   - `assign_task`
   - `complete_task`
   - `snooze_task`
   - `summarize_tasks`
   - `list_overdue_tasks`

3. Implement entity extraction:
   - title/action
   - assignee
   - recipient
   - due date
   - reminder time
   - priority

4. Implement clarification handling:
   - missing assignee
   - missing reminder time
   - ambiguous contact/user

5. Add tests with fake LLM outputs and rule-based examples.

## Acceptance Criteria

- [ ] General reminders can be created from natural language.
- [ ] Assignment commands create task and assignment.
- [ ] Missing due date or assignee prompts clarification.
- [ ] Snooze and complete commands update existing tasks only when the target task is clear.
- [ ] Agent does not act across tenant boundaries.

## Test Cases

- "Remind me to call Suresh tomorrow morning" creates task and reminder.
- "Assign Priya to submit report by Friday" creates assigned task.
- "Snooze this to Monday" updates active task when context has task ID.
- "Complete the report task" asks clarification when multiple tasks match.
- Staff cannot complete another user's task without permission.

## Validation

```bash
cd backend
python -m pytest tests/unit/agents/test_general_task_agent.py -v
python -m pytest tests/integration/test_general_agent_command_flow.py -v
```

