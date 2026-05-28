---
title: "[ATM-007] [Story] Insurance Agent MVP"
labels: [story, backend, frontend, insurance, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-007 - Insurance Agent MVP

## Objective

Deliver the first production vertical for insurance agents: policy premium reminders, renewal reminders, lead/demo follow-ups, response capture, and escalation.

## Implementation Steps

1. Implement insurance models and services:
   - policy CRUD
   - lead/demo CRUD
   - renewal workflow start
   - follow-up workflow start
   - status updates

2. Implement renewal workflow:
   - stages: expiry -10, -5, -2, 0, +1
   - customer reminders through preferred channel
   - optional copy/escalation to assigned agent
   - cancel remaining reminders when renewed
   - create escalation task when not renewed by expiry +1

3. Implement demo/lead follow-up workflow:
   - trigger when demo is logged
   - remind assigned agent after configurable X days
   - statuses: interested, renewed, not interested, follow-up later
   - reschedule on follow-up later

4. Add message templates:
   - premium due soon
   - policy expires today
   - policy expired
   - agent follow-up
   - renewal confirmation

5. Add APIs:
   - `POST /api/v1/insurance/policies`
   - `GET /api/v1/insurance/policies`
   - `PATCH /api/v1/insurance/policies/{policy_id}`
   - `POST /api/v1/insurance/policies/{policy_id}/renewal-workflow`
   - `POST /api/v1/insurance/leads`
   - `POST /api/v1/insurance/leads/{lead_id}/follow-up-workflow`
   - `GET /api/v1/insurance/dashboard`

6. Extend Insurance Agent:
   - extract policyholder, policy type, expiry date, premium amount
   - create policy from natural language command
   - start renewal workflow
   - update lead outcome from replies

## Acceptance Criteria

- [ ] Agent can create policy and start renewal reminders.
- [ ] Customer receives reminders through Telegram or WhatsApp based on preference.
- [ ] Customer renewal cancels future reminders.
- [ ] Missed renewal creates escalation task.
- [ ] Agent can log demo and get follow-up reminder.
- [ ] Insurance dashboard shows due renewals, expired policies, and pending follow-ups.

## Test Cases

- Policy expiring in 20 days creates five scheduled reminders.
- Policy expiring in 3 days creates only applicable future reminders.
- Renewal status cancels remaining reminders.
- Expiry +1 without renewal creates escalation task.
- Lead marked not interested closes lead cycle.
- Follow-up later reschedules reminder.

## Validation

```bash
cd backend
python -m pytest tests/unit/insurance/test_renewal_workflow.py -v
python -m pytest tests/unit/insurance/test_lead_followup_workflow.py -v
python -m pytest tests/integration/test_insurance_api.py -v
```

