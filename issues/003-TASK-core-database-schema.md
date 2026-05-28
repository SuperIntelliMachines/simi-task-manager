---
title: "[ATM-003] [Task] Core Database Schema and Migrations"
labels: [task, backend, database, alembic, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-003 - Core Database Schema and Migrations

## Objective

Implement the shared database foundation for tenants, users, contacts, channels, tasks, reminders, messages, workflows, agents, and audit events.

## Implementation Steps

1. Create SQLAlchemy models for:
   - `organizations`
   - `users`
   - `organization_memberships`
   - `contacts`
   - `channel_connections`
   - `contact_channel_identities`
   - `tasks`
   - `task_assignments`
   - `reminders`
   - `reminder_attempts`
   - `inbound_messages`
   - `outbound_messages`
   - `workflow_templates`
   - `workflow_runs`
   - `agent_definitions`
   - `agent_invocations`
   - `audit_events`
   - `domain_entities`

2. Add vertical MVP tables:
   - `insurance_policies`
   - `insurance_leads`
   - `construction_projects`
   - `construction_sites`
   - `medical_task_contexts`

3. Add constraints:
   - Tenant-owned tables include `organization_id`.
   - Unique dedupe key for reminders: `(organization_id, dedupe_key)`.
   - Unique inbound provider message key: `(channel, external_message_id)`.
   - Contact/user channel identity uniqueness.
   - Assignment recipient check constraints.

4. Add indexes:
   - `tasks(organization_id, status, due_at)`
   - `tasks(organization_id, domain, status)`
   - `reminders(organization_id, status, scheduled_for)`
   - `outbound_messages(organization_id, status, created_at)`
   - `audit_events(organization_id, entity_type, entity_id, created_at)`
   - `insurance_policies(organization_id, expiry_date, status)`

5. Generate Alembic migration.

6. Add seed data:
   - one organization
   - owner/admin user
   - system agent definitions
   - insurance workflow templates

## Acceptance Criteria

- [ ] All models are async SQLAlchemy compatible.
- [ ] Alembic migration applies cleanly to a fresh PostgreSQL database.
- [ ] Tenant isolation columns exist on all tenant-owned records.
- [ ] Reminder deduplication constraint exists.
- [ ] Seed data can be inserted idempotently.

## Test Cases

- Create organization, user, membership, contact, task, assignment, reminder.
- Attempt duplicate reminder dedupe key and verify failure.
- Attempt assignment with both user and contact set and verify failure.
- Verify insurance policy can link to policyholder contact and assigned agent.
- Verify cross-tenant IDs are rejected at service layer.

## Validation

```bash
cd backend
alembic upgrade head
python -m pytest tests/unit/test_models.py -v
python -m pytest tests/integration/test_database_constraints.py -v
```

