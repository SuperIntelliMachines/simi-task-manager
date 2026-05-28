---
title: "[ATM-009] [Story] Doctors Office Agent MVP"
labels: [story, backend, frontend, medical-office, compliance, P1]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-009 - Doctors Office Agent MVP

## Objective

Support doctors' offices with privacy-aware internal task management for appointment preparation, insurance verification, referrals, billing follow-up, and staff reminders.

## Implementation Steps

1. Implement medical office task service:
   - create internal staff task
   - attach minimal appointment context
   - mark sensitivity as `phi_possible` by default when patient-specific terms are present
   - restrict external messaging

2. Implement privacy guardrails:
   - role-based redaction
   - no patient-specific outbound external messages without approval
   - audit all access to sensitive task context
   - mask sensitive fields in logs

3. Implement workflows:
   - appointment prep task
   - insurance verification task
   - referral follow-up task
   - billing follow-up task

4. Extend Doctors Office Agent:
   - classify office task type
   - extract due date, assignee, appointment time, and minimal patient reference
   - ask clarification when patient identity or assignee is ambiguous

5. Add APIs:
   - `POST /api/v1/medical-office/tasks`
   - `GET /api/v1/medical-office/tasks`
   - `GET /api/v1/medical-office/dashboard`

## Acceptance Criteria

- [ ] Staff can create privacy-sensitive internal tasks.
- [ ] Unauthorized users see redacted sensitive details.
- [ ] Doctors Office Agent marks patient-related work as `phi_possible`.
- [ ] External patient messages require approval and allowed channel policy.
- [ ] Audit events record sensitive context access and updates.

## Test Cases

- Patient-specific command creates task with `phi_possible`.
- Viewer role cannot see patient-sensitive details.
- Staff assignee can see assigned task details.
- External WhatsApp message with patient details requires approval.
- Audit event is written when sensitive context is read.
- Ambiguous patient command asks clarification.

## Validation

```bash
cd backend
python -m pytest tests/unit/medical_office/test_privacy_guardrails.py -v
python -m pytest tests/unit/medical_office/test_medical_task_service.py -v
python -m pytest tests/integration/test_medical_office_api.py -v
```

