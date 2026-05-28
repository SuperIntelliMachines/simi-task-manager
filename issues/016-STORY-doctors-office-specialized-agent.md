---
title: "[ATM-016] [Story] Doctors Office Specialized Agent"
labels: [story, backend, ai, agents, medical-office, compliance, P1]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-016 - Doctors Office Specialized Agent

## Objective

Implement the Doctors Office Agent for privacy-aware internal tasks such as appointment preparation, insurance verification, referral follow-up, billing follow-up, and staff reminders.

## Implementation Steps

1. Implement Doctors Office Agent prompt and policy:
   - domain: `doctors_office`
   - patient-specific content defaults to `phi_possible`
   - external patient messages require approval and allowed channel policy
   - clinical details must not be sent externally by default

2. Implement intents:
   - `create_appointment_prep_task`
   - `create_insurance_verification_task`
   - `create_referral_followup_task`
   - `create_billing_followup_task`
   - `assign_staff_task`
   - `summarize_office_tasks`
   - `list_overdue_sensitive_tasks`

3. Implement entity extraction:
   - patient reference
   - appointment date/time
   - staff assignee
   - office task type
   - due date
   - referral/billing context

4. Implement workflow mapping:
   - internal staff reminder
   - appointment prep checklist
   - billing/referral follow-up
   - sensitive context redaction

5. Implement clarification handling:
   - ambiguous patient
   - missing appointment time
   - missing assignee
   - unclear whether message is internal or external

6. Implement approval handling:
   - any patient-specific external message
   - messages containing diagnosis/treatment/lab/medication details
   - sensitive task visibility for unauthorized roles

## Acceptance Criteria

- [ ] Patient-specific commands create tasks marked `phi_possible`.
- [ ] Internal staff reminders can be created.
- [ ] External patient messages require approval.
- [ ] Unauthorized viewers see redacted task details.
- [ ] Sensitive context access creates audit events.
- [ ] Ambiguous patient commands ask clarification.

## Test Cases

- "Verify insurance for tomorrow's 10 AM patient appointment" creates `phi_possible` task.
- "Remind front desk to call Maria about referral" creates internal task with sensitive context.
- "Text patient their lab result is ready" returns approval-required or rejected based on policy.
- Viewer role cannot see patient-sensitive details.
- Staff assignee can see assigned sensitive task.
- Ambiguous patient name asks which patient.

## Validation

```bash
cd backend
python -m pytest tests/unit/agents/test_doctors_office_agent.py -v
python -m pytest tests/integration/test_doctors_office_agent_command_flow.py -v
```

