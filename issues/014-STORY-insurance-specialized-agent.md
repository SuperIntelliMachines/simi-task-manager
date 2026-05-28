---
title: "[ATM-014] [Story] Insurance Specialized Agent"
labels: [story, backend, ai, agents, insurance, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-014 - Insurance Specialized Agent

## Objective

Implement the Insurance Agent that understands policies, premiums, renewals, demos, leads, and agent follow-up workflows.

## Implementation Steps

1. Implement Insurance Agent prompt and policy:
   - domain: `insurance`
   - allowed tools: contact, policy, lead, task, reminder, workflow, message draft tools
   - guardrails for consent, verified channel identity, and bulk messages

2. Implement intents:
   - `create_policy`
   - `create_policy_renewal_workflow`
   - `create_premium_reminder`
   - `log_demo`
   - `create_lead_followup`
   - `mark_policy_renewed`
   - `mark_lead_not_interested`
   - `reschedule_followup`
   - `summarize_renewals`

3. Implement entity extraction:
   - policyholder name/contact
   - policy type
   - expiry date
   - premium amount
   - carrier
   - policy number
   - assigned agent
   - preferred channel

4. Implement workflow mapping:
   - policy renewal workflow with expiry -10, -5, -2, 0, +1
   - demo follow-up workflow
   - escalation task on missed renewal

5. Implement clarification handling:
   - missing expiry date
   - unknown policyholder
   - missing channel preference
   - multiple matching policies

6. Implement approval handling:
   - bulk customer reminders
   - unverified customer channel
   - first outbound customer message without consent

## Acceptance Criteria

- [ ] Natural language can create policy plus renewal workflow.
- [ ] Agent skips renewal reminder stages already in the past.
- [ ] Policy renewal cancels remaining reminders.
- [ ] Demo follow-up creates assigned agent reminder.
- [ ] Missing policy expiry asks clarification.
- [ ] Bulk campaign requires approval.

## Test Cases

- "Create auto policy for Ravi expiring June 25 and remind him on WhatsApp" creates policy and workflow.
- "Renewed Ravi's policy" marks matching policy renewed and cancels reminders.
- "Follow up with Priya after demo in 3 days" creates lead follow-up task.
- "Send renewal reminders to all expiring customers" returns approval-required.
- Unknown customer asks for contact details.
- Multiple policies for same customer asks which policy.

## Validation

```bash
cd backend
python -m pytest tests/unit/agents/test_insurance_agent.py -v
python -m pytest tests/integration/test_insurance_agent_command_flow.py -v
```

