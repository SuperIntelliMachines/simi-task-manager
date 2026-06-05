# Admin Portal Design

## Purpose

Build an internal admin portal for managing customer tenants, subscriptions/configuration, enabled agents, communication channels, usage, support access, and operational health.

This portal is for platform operators and authorized support users. It is separate from the customer-facing task manager experience.

## Admin Personas

### Platform Admin

Owns customer onboarding, tenant configuration, billing/subscription status, agent enablement, and production support.

Needs:

- Create and configure customer tenants.
- Enable/disable specialized agents.
- Configure allowed channels.
- View health and usage.
- Manage support access.
- Inspect audit history.

### Support Engineer

Troubleshoots customer issues with strict, audited access.

Needs:

- See failed reminders/messages.
- Replay failed jobs safely.
- Inspect channel configuration health without seeing secrets.
- Access tenant data only through approved support sessions.

### Implementation Manager

Onboards new customers and validates workflows before go-live.

Needs:

- Checklist-driven onboarding.
- Configure customer industry template.
- Configure users, contacts, channels, and message templates.
- Run test messages and sample workflows.

## Admin Portal Navigation

```text
Admin Portal
|-- Customers
|   |-- Customer List
|   |-- Customer Detail
|   |-- Users & Roles
|   |-- Agents & Workflows
|   |-- Channels
|   |-- Message Templates
|   |-- Usage & Health
|   `-- Audit Log
|-- Approvals
|-- Failed Reminders
|-- Agent Invocations
|-- System Health
`-- Settings
```

## Customer List

Purpose:

- Show all tenant customers and their operational state.

Columns:

- Customer name
- Slug
- Status
- Industry/template
- Enabled agents
- Active users
- Open tasks
- Failed reminders in last 24 hours
- Last activity
- Subscription/status

Filters:

- Status: active, onboarding, suspended, churned
- Industry: insurance, construction, medical office, general
- Agent enabled
- Health: healthy, warning, critical

Actions:

- Create customer
- Open customer detail
- Suspend/reactivate customer
- Start support access request

## Customer Detail

Sections:

- Overview
- Onboarding checklist
- Users and roles
- Contacts
- Agents and workflows
- Channels
- Message templates
- Usage and billing
- Operational health
- Audit log

Important metrics:

- Open tasks
- Overdue tasks
- Pending approvals
- Messages sent today
- Failed messages
- Agent invocations today
- Token usage estimate
- Active workflows

## Customer Onboarding Flow

1. Create organization:
   - name
   - slug
   - timezone
   - industry template
   - subscription plan

2. Create owner user:
   - name
   - email
   - phone
   - role: owner

3. Enable agents:
   - General Task Agent
   - Insurance Agent for insurance customers
   - Construction Agent for construction customers
   - Doctors Office Agent only after privacy review
   - mark one specialized agent as the tenant primary agent
   - store tenant agent assignment in `organization_agent_configs`

4. Configure channels:
   - Telegram bot connection
   - WhatsApp Business connection
   - test message
   - webhook status check

5. Configure message templates:
   - choose system defaults
   - customize customer wording
   - approve templates
   - map WhatsApp provider template names

6. Configure notification preferences:
   - default channel by purpose
   - quiet hours
   - fallback channel
   - consent policy

7. Run sample workflow:
   - create test task
   - send test reminder
   - receive test reply
   - validate audit event

8. Mark tenant ready for go-live.

## Agents & Workflows Management

The admin can:

- Enable/disable agents per tenant.
- Set the tenant primary specialized agent.
- View agent definitions and current versions.
- Configure workflow templates.
- Configure industry defaults.
- Review recent agent invocations.
- Disable an agent if it causes unsafe behavior.

Agent controls:

- status
- primary tenant agent flag
- allowed tools
- approval policy
- max bulk action size
- sensitive-data policy
- enabled channels

## Channel Management

Telegram card:

- connection status
- bot username
- webhook URL
- webhook verified status
- linked groups/chats
- test message action
- last inbound message
- last outbound message

WhatsApp card:

- connection status
- phone number ID
- business account label
- webhook verified status
- template sync status
- test message action
- last inbound message
- last outbound message

Security rules:

- Never display provider access tokens.
- Show only secret reference and connection health.
- Channel setting changes require admin role.
- Channel setting changes create audit events.

## Message Templates Management

Capabilities:

- List templates by domain, channel, purpose, status, and language.
- Create/edit draft templates.
- Preview with sample data.
- Submit for approval.
- Approve/archive templates.
- Map WhatsApp provider template names.

Template statuses:

- draft
- pending approval
- approved
- archived

## Approval Queue

Shows approval requests across tenants.

Columns:

- Customer
- Domain
- Requested by
- Agent
- Action type
- Sensitivity
- Reason
- Created at
- Expires at
- Status

Actions:

- View proposed actions
- View message preview
- Approve
- Reject
- Add decision note

## Failed Reminders and Replay

Purpose:

- Let support identify failed reminder/message deliveries and replay safely.

Columns:

- Customer
- Reminder
- Recipient
- Channel
- Stage
- Attempt count
- Last error
- Last attempted
- Status

Actions:

- View attempts
- Retry
- Cancel
- Mark resolved

Replay safety:

- Check reminder status before replay.
- Check outbound provider message ID.
- Check dedupe key.
- Write audit event for replay.

## Support Access

Support access must be explicit and audited.

Flow:

1. Platform admin requests access to customer tenant.
2. Reason and expiry are required.
3. Access creates audit event.
4. Every sensitive read/write during support session is audited.
5. Access expires automatically.
6. Customer-facing audit can show support session history if required.

Support access fields:

- customer
- support user
- reason
- approved by
- expires at
- status

## Admin Portal API

Customer management:

- `GET /api/v1/admin/customers`
- `POST /api/v1/admin/customers`
- `GET /api/v1/admin/customers/{organization_id}`
- `PATCH /api/v1/admin/customers/{organization_id}`

Customer operations:

- `GET /api/v1/admin/customers/{organization_id}/health`
- `GET /api/v1/admin/customers/{organization_id}/usage`
- `GET /api/v1/admin/customers/{organization_id}/audit`
- `POST /api/v1/admin/customers/{organization_id}/suspend`
- `POST /api/v1/admin/customers/{organization_id}/reactivate`

Support access:

- `POST /api/v1/admin/customers/{organization_id}/support-access`
- `POST /api/v1/admin/customers/{organization_id}/disable-support-access`

Operational queues:

- `GET /api/v1/admin/approval-requests`
- `GET /api/v1/admin/failed-reminders`
- `POST /api/v1/admin/failed-reminders/{reminder_id}/retry`
- `GET /api/v1/admin/agent-invocations`

## Frontend UX

Use a dense operational UI, not a marketing layout. The visual design should follow the established GyantrAI product experience: premium AI-era polish, clean Tailwind/Radix/shadcn-style components, lucide icons, refined interaction states, responsive layouts, and consistent theme tokens.

The admin portal should feel like an AI control plane: efficient, high-signal, and polished. It should not feel like a generic CRUD admin template.

Primary admin screens:

- Customer list table.
- Customer detail with tabs.
- Onboarding checklist.
- Channel connection cards.
- Message template editor.
- Approval detail drawer.
- Failed reminder detail drawer.
- Audit log table.

Design rules:

- Reuse or mirror GyantrAI typography, spacing, color tokens, component styling, navigation patterns, and interaction patterns where possible.
- Use compact tables for operational data.
- Use badges for status and health.
- Use skeletons, clear empty states, error states, optimistic feedback where appropriate, and toast notifications for completed actions.
- Use clear destructive-action confirmations.
- Use lucide icons for actions.
- Do not expose secrets.
- Keep support access and replay actions visually distinct.

## Admin Database Additions

The core `organizations`, `users`, `organization_memberships`, `audit_events`, `approval_requests`, `channel_connections`, `message_templates`, and `agent_invocations` tables support most admin features.

Add `support_access_sessions`.

### support_access_sessions

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `support_user_id uuid not null references users(id)`
- `approved_by_user_id uuid references users(id)`
- `reason text not null`
- `status text not null default 'active'`
- `started_at timestamptz not null`
- `expires_at timestamptz not null`
- `ended_at timestamptz`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Statuses:

- `pending`
- `active`
- `expired`
- `revoked`

## Testing

Backend tests:

- Platform admin can create customer.
- Non-admin cannot access admin endpoints.
- Customer creation seeds owner membership and selected agents.
- Channel health endpoint masks secrets.
- Support access expires and blocks further access.
- Failed reminder replay is idempotent.
- Admin actions write audit events.

Frontend tests:

- Customer list renders status and health.
- Customer onboarding checklist advances after completed setup.
- Channel cards hide secrets.
- Approval drawer approves/rejects request.
- Failed reminder replay requires confirmation.
- Support access form requires reason and expiry.

E2E smoke tests:

- Create insurance customer.
- Enable Insurance Agent.
- Configure mock WhatsApp channel.
- Send test message.
- Create sample policy renewal workflow.
- Verify audit events and health metrics.
