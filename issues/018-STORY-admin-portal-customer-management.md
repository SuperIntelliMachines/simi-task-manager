---
title: "[ATM-018] [Story] Admin Portal for Customer Management"
labels: [story, frontend, backend, admin, customer-management, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-018 - Admin Portal for Customer Management

## Objective

Build an internal admin portal for managing customer tenants, onboarding, users, enabled agents, channels, message templates, usage, support access, failed reminders, and audit history.

The admin portal should use the same GyantrAI-aligned visual system as the customer task workbench: polished Tailwind/Radix/shadcn-style components, lucide icons, refined loading/empty/error states, and responsive layouts. Keep the admin experience dense and operational, but make it feel like a premium AI-era control plane rather than a plain CRUD back office.

## Reference

Read `docs/admin-portal-design.md`.

## Implementation Steps

1. Add backend admin authorization:
   - platform admin role
   - support engineer role
   - implementation manager role
   - deny admin APIs to tenant-only users

2. Add `support_access_sessions` model and migration.

3. Implement customer management APIs:
   - `GET /api/v1/admin/customers`
   - `POST /api/v1/admin/customers`
   - `GET /api/v1/admin/customers/{organization_id}`
   - `PATCH /api/v1/admin/customers/{organization_id}`
   - suspend/reactivate endpoints

4. Implement customer onboarding APIs:
   - create owner user
   - enable agents
   - assign one primary specialized agent for the tenant
   - configure default workflow templates
   - configure default message templates
   - run sample workflow

5. Implement operational APIs:
   - customer health
   - customer usage
   - customer audit
   - failed reminders
   - failed reminder retry
   - agent invocation list
   - support access create/revoke

6. Build frontend admin portal:
   - GyantrAI-aligned app shell, theme tokens, navigation, tables, tabs, drawers, forms, dialogs, and status badges
   - customer list
   - customer detail tabs
   - onboarding checklist
   - users and roles tab
   - agents and workflows tab
   - channel connection cards
   - message templates tab
   - usage and health tab
   - audit log tab
   - approval queue
   - failed reminder queue

7. Add safety UX:
   - confirmation for suspend/reactivate
   - confirmation for failed reminder replay
   - reason and expiry required for support access
   - never display secrets
   - audit all admin actions

## Acceptance Criteria

- [ ] Platform admin can create and configure a customer tenant.
- [ ] Admin can enable Insurance Agent and mark it as the tenant primary specialized agent for an insurance customer.
- [ ] Admin can configure Telegram/WhatsApp channel placeholders and send test message.
- [ ] Admin can view failed reminders and retry safely.
- [ ] Admin can view approval requests and agent invocations.
- [ ] Support access requires reason and expiry.
- [ ] Admin portal follows the GyantrAI-style rich AI control-plane UX while preserving dense operational workflows.
- [ ] Admin portal masks all secrets.
- [ ] All admin changes write audit events.

## Test Cases

- Non-admin receives forbidden response for admin customer list.
- Creating customer creates organization and owner membership.
- Enabling agent creates tenant agent configuration with primary agent selection.
- Channel health response does not expose provider token.
- Failed reminder retry checks dedupe and does not duplicate sent message.
- Support access expires and blocks subsequent tenant access.
- Customer list filters by status, industry, and health.
- Onboarding checklist reflects setup progress.
- Admin tables, tabs, drawers, dialogs, loading states, empty states, and destructive confirmations match the GyantrAI-aligned theme.

## Validation

```bash
cd backend
python -m pytest tests/unit/admin/test_admin_permissions.py -v
python -m pytest tests/integration/admin/test_customer_management_api.py -v
python -m pytest tests/integration/admin/test_support_access.py -v

cd ../frontend
npm run typecheck
npm run test -- --run Admin
npm run build
```
