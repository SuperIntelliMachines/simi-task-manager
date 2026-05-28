# Agentic AI Task Manager Platform Specification

## Purpose

Build a reusable AI task-management platform where specialized line-of-business agents understand domain-specific work, but all agents run on the same task, workflow, reminder, messaging, permissions, and audit foundation.

The first production vertical is insurance agents who need policy premium reminders, renewal reminders, demo follow-ups, and escalation to the agent. The same platform must also support construction teams and doctors' offices through specialized agents and templates.

## Product Positioning

The product is not a single insurance reminder bot. It is:

> A generic AI task manager powered by specialized business agents.

Core platform responsibilities stay generic:

- Task creation, assignment, status, reminders, escalation, comments, and audit history.
- Communication through selected customer channels such as Telegram and WhatsApp.
- Workflow templates and scheduled jobs.
- AI orchestration, entity extraction, task planning, and message drafting.
- Tenant isolation, permissions, compliance guardrails, and observability.

Specialized agents provide business knowledge:

- Insurance Agent: policies, premiums, renewals, quotes, demos, leads.
- Construction Agent: projects, sites, workers, work orders, completion proof, owner updates.
- Doctors Office Agent: office tasks, appointments, patient follow-up, referrals, billing, privacy-sensitive handling.
- General Task Agent: fallback for non-vertical tasks.

## Reference Tech Stack

Use the same stack pattern as the GyantrAI `dev` branch.

Backend:

- Python 3.11+
- FastAPI
- Pydantic v2 and pydantic-settings
- SQLAlchemy 2.0 async
- Alembic migrations
- PostgreSQL 15+
- Redis 7+
- Celery for background jobs
- LangChain-compatible LLM integration with OpenAI/Anthropic support
- httpx for external APIs
- pytest, pytest-asyncio, pytest-cov
- ruff, black, mypy

Frontend:

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Radix/shadcn-style components
- TanStack Query
- React Hook Form
- Zod
- Zustand where local state is needed
- Recharts for reporting
- lucide-react icons
- Vitest, React Testing Library, MSW
- Playwright for end-to-end smoke tests

Deployment and operations:

- Docker
- Cloud Run or equivalent container runtime
- Cloud SQL PostgreSQL
- Memorystore/Redis or equivalent
- Secret Manager
- CI checks for backend tests, frontend tests, lint, type checks, and migrations

## Personas

### Tenant Owner

The business owner or primary administrator. Chooses enabled agents, channels, message templates, escalation rules, and staff permissions.

Needs:

- Business overview across all work.
- Ability to configure workflows without code.
- Compliance visibility and audit history.
- Channel setup for Telegram and WhatsApp.

### Manager

Supervises tasks and people. In insurance this can be an agency manager. In construction this can be a project manager. In a doctors' office this can be an office manager.

Needs:

- View workload by assignee, customer, project, policy, or office function.
- Reassign, escalate, and approve sensitive outbound messages.
- Receive summaries and missed-task reports.

### Staff/Assignee

The person responsible for completing tasks. Examples: insurance agent, site worker, front-desk staff, billing staff.

Needs:

- Simple task list.
- Channel reminders.
- Quick status updates from Telegram/WhatsApp or web.
- Minimal friction for completion, snooze, or follow-up later.

### External Contact

Customer, policyholder, worker, owner, vendor, patient, or other non-staff recipient.

Needs:

- Clear reminders on their preferred channel.
- Ability to reply with simple status.
- Opt-out and consent controls.
- No exposure to internal notes.

### Platform Admin

Internal operator managing deployments and customer support.

Needs:

- Tenant health.
- Failed job and failed message diagnostics.
- Audit access with strict internal controls.
- Safe replays for stuck reminders or messages.

## Target User Journeys

### Insurance

1. Agent enters or messages: "Follow up with Ravi about his term policy demo in 3 days."
2. AI identifies the Insurance Agent domain.
3. The system creates a lead follow-up task assigned to the agent.
4. Reminder is sent to the agent on the due date.
5. Agent marks "interested", "not interested", or "follow-up later".
6. If follow-up later, the task is rescheduled with a new reminder.

Premium renewal journey:

1. Policy is created with holder, expiry date, premium amount, product, and preferred channel.
2. Insurance Agent template creates reminder stages at expiry -10, -5, -2, 0, and +1 days.
3. Customer receives reminders on Telegram or WhatsApp based on preference and consent.
4. If customer renews, remaining reminders are canceled.
5. If renewal is not captured by expiry +1, an escalation task is created for the agent.

### Construction

1. Project manager says in Telegram: "Assign Ravi to complete wiring at Site A by tomorrow."
2. Construction Agent extracts worker, site, work item, and due date.
3. A task is created and assigned to Ravi.
4. Ravi receives a WhatsApp or Telegram reminder.
5. Ravi replies "done" and optionally uploads a photo.
6. Manager receives a completion update.
7. Owner receives an approved summary if the workflow requires external reporting.

### Doctors Office

1. Office manager says: "Remind front desk to verify insurance for tomorrow's 10 AM appointment."
2. Doctors Office Agent creates an internal staff task.
3. The system classifies the task as privacy-sensitive.
4. Patient-identifying data is limited to authorized staff and approved channels.
5. Completion is tracked with audit history.

## Agentic Architecture

```text
                         Web App
              React + TypeScript + Vite
                              |
                              v
                      FastAPI API Layer
                              |
        +---------------------+---------------------+
        |                                           |
        v                                           v
 Core Task/Workflow Engine                  AI Orchestrator
        |                                           |
        |                         +-----------------+-----------------+
        |                         |                 |                 |
        v                         v                 v                 v
 PostgreSQL                 General Agent     Insurance Agent   Construction Agent
        |                         |                 |                 |
        v                         +-----------------+-----------------+
 Redis/Celery Jobs                            |
        |                                      v
        v                              Doctors Office Agent
 Reminder Processor
        |
        v
 Channel Service
        |
 +------+------+
 |             |
 v             v
Telegram    WhatsApp
```

## Runtime Agent Flow

```text
Inbound message or web request
        |
        v
Authenticate tenant and actor
        |
        v
Normalize input into a channel-agnostic message
        |
        v
Run safety and scope guardrails
        |
        v
Classify intent and business domain
        |
        v
Route to specialized agent
        |
        v
Extract entities and propose actions
        |
        v
Validate required fields, permissions, and confidence
        |
        +---- low confidence or sensitive action ----> ask clarification or require approval
        |
        v
Create/update tasks, reminders, workflows, messages
        |
        v
Write audit events
        |
        v
Return confirmation to user
```

## Core Domain Model

The platform uses generic records for most behavior and optional vertical records for domain-specific details.

Generic records:

- Organization and tenant data.
- Users, roles, memberships, and personas.
- Contacts and channel identities.
- Tasks, assignments, reminders, messages, comments, attachments, and audit events.
- Workflow templates and workflow runs.
- Agent definitions, agent invocations, tools, and guardrail decisions.
- Agent sessions and conversation context for clarifications.
- Approval requests for sensitive, bulk, or externally visible actions.
- Message templates for approved Telegram and WhatsApp communication.
- Notification preferences for contacts and internal users.
- Domain entities for flexible vertical expansion.

Vertical records:

- Insurance policies, premiums, leads, demos, renewals.
- Construction projects, sites, workers, work orders, owner updates.
- Doctors office appointments, patient task references, referral tasks, billing tasks.

## Database Design

Use UUID primary keys, `created_at`, `updated_at`, and soft-delete where business records should remain auditable. Every tenant-owned table must include `organization_id`.

### organizations

Stores tenants.

Columns:

- `id uuid primary key`
- `name text not null`
- `slug text unique not null`
- `status text not null default 'active'`
- `default_timezone text not null default 'UTC'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### users

Stores internal users.

Columns:

- `id uuid primary key`
- `email text unique not null`
- `display_name text not null`
- `phone_e164 text`
- `status text not null default 'active'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### organization_memberships

Maps users to tenants and roles.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `user_id uuid not null references users(id)`
- `role text not null`
- `persona text not null`
- `status text not null default 'active'`
- `created_at timestamptz not null`
- unique `(organization_id, user_id)`

Allowed roles:

- `owner`
- `admin`
- `manager`
- `staff`
- `viewer`
- `platform_support`

Allowed personas:

- `tenant_owner`
- `manager`
- `assignee`
- `external_contact`
- `platform_admin`

### contacts

Stores external contacts and non-login recipients.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `display_name text not null`
- `contact_type text not null`
- `email text`
- `phone_e164 text`
- `preferred_channel text`
- `language_code text default 'en'`
- `timezone text`
- `consent_status text not null default 'unknown'`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Contact types:

- `customer`
- `policyholder`
- `worker`
- `owner`
- `patient`
- `vendor`
- `other`

### channel_connections

Stores tenant-level channel configuration.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `channel text not null`
- `display_name text not null`
- `status text not null default 'inactive'`
- `config jsonb not null default '{}'`
- `secret_ref text`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(organization_id, channel, display_name)`

Channels:

- `telegram`
- `whatsapp`
- `email`
- `web`

MVP requires Telegram and WhatsApp.

### contact_channel_identities

Maps contacts or users to channel identities.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `contact_id uuid references contacts(id)`
- `user_id uuid references users(id)`
- `channel text not null`
- `external_id text not null`
- `username text`
- `phone_e164 text`
- `is_verified boolean not null default false`
- `created_at timestamptz not null`
- unique `(organization_id, channel, external_id)`

Constraint: exactly one of `contact_id` or `user_id` must be set.

### notification_preferences

Stores recipient-level channel, quiet-hour, and opt-out preferences. This table should be checked before every external outbound message and before non-urgent internal reminders.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `contact_id uuid references contacts(id)`
- `user_id uuid references users(id)`
- `purpose text not null`
- `preferred_channel text not null`
- `fallback_channel text`
- `quiet_hours_start time`
- `quiet_hours_end time`
- `timezone text`
- `is_enabled boolean not null default true`
- `consent_status text not null default 'unknown'`
- `opted_out_at timestamptz`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(organization_id, contact_id, user_id, purpose)`

Constraint: exactly one of `contact_id` or `user_id` must be set.

Purposes:

- `task_reminder`
- `policy_renewal`
- `premium_reminder`
- `lead_followup`
- `worker_task`
- `owner_update`
- `medical_office_internal`
- `system_alert`

### tasks

Generic task record.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `title text not null`
- `description text`
- `status text not null default 'open'`
- `priority text not null default 'normal'`
- `domain text not null default 'general'`
- `source text not null default 'manual'`
- `created_by_user_id uuid references users(id)`
- `created_by_agent_id uuid references agent_definitions(id)`
- `primary_contact_id uuid references contacts(id)`
- `due_at timestamptz`
- `completed_at timestamptz`
- `closed_reason text`
- `sensitivity text not null default 'normal'`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Statuses:

- `open`
- `in_progress`
- `waiting`
- `completed`
- `canceled`
- `failed`

Domains:

- `general`
- `insurance`
- `construction`
- `doctors_office`

Sensitivity:

- `normal`
- `confidential`
- `regulated`
- `phi_possible`

### task_assignments

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `task_id uuid not null references tasks(id)`
- `assignee_user_id uuid references users(id)`
- `assignee_contact_id uuid references contacts(id)`
- `assignment_type text not null default 'owner'`
- `status text not null default 'active'`
- `created_at timestamptz not null`

Constraint: exactly one of `assignee_user_id` or `assignee_contact_id` must be set.

### reminders

Stores reminder schedules independent from delivery attempts.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `task_id uuid references tasks(id)`
- `workflow_run_id uuid references workflow_runs(id)`
- `recipient_user_id uuid references users(id)`
- `recipient_contact_id uuid references contacts(id)`
- `channel text not null`
- `scheduled_for timestamptz not null`
- `status text not null default 'scheduled'`
- `stage_key text`
- `template_key text`
- `dedupe_key text not null`
- `payload jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(organization_id, dedupe_key)`

Statuses:

- `scheduled`
- `processing`
- `sent`
- `acknowledged`
- `snoozed`
- `canceled`
- `failed`

### reminder_attempts

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `reminder_id uuid not null references reminders(id)`
- `attempt_number integer not null`
- `channel text not null`
- `provider_message_id text`
- `status text not null`
- `error_code text`
- `error_message text`
- `sent_at timestamptz`
- `created_at timestamptz not null`

### inbound_messages

Columns:

- `id uuid primary key`
- `organization_id uuid references organizations(id)`
- `channel text not null`
- `external_message_id text not null`
- `sender_user_id uuid references users(id)`
- `sender_contact_id uuid references contacts(id)`
- `raw_payload jsonb not null`
- `normalized_text text`
- `attachments jsonb not null default '[]'`
- `processed_status text not null default 'pending'`
- `received_at timestamptz not null`
- `created_at timestamptz not null`
- unique `(channel, external_message_id)`

### outbound_messages

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `channel text not null`
- `recipient_user_id uuid references users(id)`
- `recipient_contact_id uuid references contacts(id)`
- `body text not null`
- `template_key text`
- `status text not null default 'queued'`
- `provider_message_id text`
- `error_code text`
- `error_message text`
- `created_by_agent_invocation_id uuid references agent_invocations(id)`
- `sent_at timestamptz`
- `created_at timestamptz not null`

### message_templates

Stores approved reusable message templates. WhatsApp business-initiated messages should map to provider-approved template names.

Columns:

- `id uuid primary key`
- `organization_id uuid references organizations(id)`
- `domain text not null`
- `channel text not null`
- `purpose text not null`
- `template_key text not null`
- `provider_template_name text`
- `language_code text not null default 'en'`
- `body text not null`
- `variables jsonb not null default '[]'`
- `status text not null default 'draft'`
- `requires_approval boolean not null default false`
- `is_system boolean not null default false`
- `created_by_user_id uuid references users(id)`
- `approved_by_user_id uuid references users(id)`
- `approved_at timestamptz`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(organization_id, channel, template_key, language_code)`

Statuses:

- `draft`
- `pending_approval`
- `approved`
- `archived`

### workflow_templates

Columns:

- `id uuid primary key`
- `organization_id uuid references organizations(id)`
- `domain text not null`
- `key text not null`
- `name text not null`
- `description text`
- `version integer not null default 1`
- `is_system boolean not null default false`
- `definition jsonb not null`
- `status text not null default 'active'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(organization_id, domain, key, version)`

Use `organization_id null` for system templates.

### workflow_runs

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `workflow_template_id uuid references workflow_templates(id)`
- `domain text not null`
- `status text not null default 'running'`
- `subject_entity_type text`
- `subject_entity_id uuid`
- `state jsonb not null default '{}'`
- `started_at timestamptz not null`
- `completed_at timestamptz`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### agent_definitions

Columns:

- `id uuid primary key`
- `key text unique not null`
- `name text not null`
- `domain text not null`
- `description text not null`
- `status text not null default 'active'`
- `system_prompt text not null`
- `tool_policy jsonb not null default '{}'`
- `guardrail_policy jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### agent_invocations

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `agent_definition_id uuid not null references agent_definitions(id)`
- `actor_user_id uuid references users(id)`
- `inbound_message_id uuid references inbound_messages(id)`
- `intent text`
- `domain text`
- `input_summary text`
- `output_summary text`
- `confidence numeric(5,4)`
- `status text not null`
- `guardrail_result jsonb not null default '{}'`
- `tool_calls jsonb not null default '[]'`
- `token_usage jsonb not null default '{}'`
- `created_at timestamptz not null`

### agent_sessions

Stores multi-turn AI context for clarifications, approvals, and channel conversations. Do not store secrets or unnecessary sensitive data. Store only the minimum context needed to resume the task safely.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `agent_definition_id uuid references agent_definitions(id)`
- `actor_user_id uuid references users(id)`
- `contact_id uuid references contacts(id)`
- `channel text`
- `external_thread_id text`
- `status text not null default 'active'`
- `current_domain text`
- `current_intent text`
- `pending_question text`
- `collected_fields jsonb not null default '{}'`
- `last_agent_invocation_id uuid references agent_invocations(id)`
- `expires_at timestamptz not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Statuses:

- `active`
- `waiting_for_user`
- `waiting_for_approval`
- `completed`
- `expired`
- `canceled`

### approval_requests

Stores actions that the AI or workflow engine may not execute without human approval.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `requested_by_user_id uuid references users(id)`
- `requested_by_agent_invocation_id uuid references agent_invocations(id)`
- `approver_user_id uuid references users(id)`
- `domain text not null`
- `action_type text not null`
- `status text not null default 'pending'`
- `sensitivity text not null default 'normal'`
- `reason text not null`
- `proposed_actions jsonb not null`
- `message_preview text`
- `entity_type text`
- `entity_id uuid`
- `decision_note text`
- `decided_by_user_id uuid references users(id)`
- `decided_at timestamptz`
- `expires_at timestamptz`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Statuses:

- `pending`
- `approved`
- `rejected`
- `expired`
- `canceled`

Approval-required examples:

- First outbound customer message without verified consent.
- Bulk customer reminders.
- Construction owner update.
- Patient-specific external medical-office message.
- Closing multiple tasks from one AI command.
- Changing tenant-level channel settings through AI.

### audit_events

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `actor_user_id uuid references users(id)`
- `actor_agent_invocation_id uuid references agent_invocations(id)`
- `event_type text not null`
- `entity_type text not null`
- `entity_id uuid not null`
- `before jsonb`
- `after jsonb`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`

### domain_entities

Generic extension point for vertical records that do not need a first-class table yet.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `domain text not null`
- `entity_type text not null`
- `display_name text not null`
- `external_ref text`
- `contact_id uuid references contacts(id)`
- `data jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### insurance_policies

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `policyholder_contact_id uuid not null references contacts(id)`
- `assigned_agent_user_id uuid references users(id)`
- `policy_number text`
- `policy_type text not null`
- `carrier_name text`
- `premium_amount numeric(12,2)`
- `premium_currency text not null default 'USD'`
- `effective_date date`
- `expiry_date date not null`
- `status text not null default 'active'`
- `preferred_channel text`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### insurance_leads

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `contact_id uuid not null references contacts(id)`
- `assigned_agent_user_id uuid references users(id)`
- `source text`
- `demo_date timestamptz`
- `status text not null default 'new'`
- `next_follow_up_at timestamptz`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### construction_projects

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `name text not null`
- `owner_contact_id uuid references contacts(id)`
- `manager_user_id uuid references users(id)`
- `status text not null default 'active'`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### construction_sites

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `project_id uuid not null references construction_projects(id)`
- `name text not null`
- `address text`
- `status text not null default 'active'`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### medical_task_contexts

Keep this table minimal for MVP. Store only the context required for office task execution. Do not store clinical notes unless the product has explicit compliance approval.

Columns:

- `id uuid primary key`
- `organization_id uuid not null references organizations(id)`
- `task_id uuid not null references tasks(id)`
- `context_type text not null`
- `patient_contact_id uuid references contacts(id)`
- `appointment_at timestamptz`
- `privacy_level text not null default 'phi_possible'`
- `data jsonb not null default '{}'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

## API Surface

Core:

- `POST /api/v1/tasks`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `PATCH /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/assignments`
- `POST /api/v1/tasks/{task_id}/comments`
- `POST /api/v1/tasks/{task_id}/complete`
- `POST /api/v1/tasks/{task_id}/snooze`
- `GET /api/v1/reminders`
- `POST /api/v1/reminders`
- `POST /api/v1/reminders/{reminder_id}/ack`

Agentic:

- `POST /api/v1/ai/command`
- `POST /api/v1/ai/classify`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_key}`
- `GET /api/v1/agent-invocations`
- `GET /api/v1/agent-sessions/{session_id}`
- `POST /api/v1/agent-sessions/{session_id}/reply`
- `GET /api/v1/approval-requests`
- `POST /api/v1/approval-requests/{approval_request_id}/approve`
- `POST /api/v1/approval-requests/{approval_request_id}/reject`

Channels:

- `GET /api/v1/channels/connections`
- `POST /api/v1/channels/connections`
- `PATCH /api/v1/channels/connections/{connection_id}`
- `POST /api/v1/telegram/webhook`
- `POST /api/v1/whatsapp/webhook`
- `POST /api/v1/channels/test-message`
- `GET /api/v1/message-templates`
- `POST /api/v1/message-templates`
- `PATCH /api/v1/message-templates/{template_id}`
- `POST /api/v1/message-templates/{template_id}/approve`
- `GET /api/v1/notification-preferences`
- `PUT /api/v1/notification-preferences/{preference_id}`

Admin portal:

- `GET /api/v1/admin/customers`
- `POST /api/v1/admin/customers`
- `GET /api/v1/admin/customers/{organization_id}`
- `PATCH /api/v1/admin/customers/{organization_id}`
- `GET /api/v1/admin/customers/{organization_id}/health`
- `GET /api/v1/admin/customers/{organization_id}/usage`
- `GET /api/v1/admin/customers/{organization_id}/audit`
- `POST /api/v1/admin/customers/{organization_id}/support-access`
- `POST /api/v1/admin/customers/{organization_id}/disable-support-access`

Insurance:

- `POST /api/v1/insurance/policies`
- `GET /api/v1/insurance/policies`
- `POST /api/v1/insurance/policies/{policy_id}/renewal-workflow`
- `POST /api/v1/insurance/leads`
- `POST /api/v1/insurance/leads/{lead_id}/follow-up-workflow`
- `GET /api/v1/insurance/dashboard`

Construction:

- `POST /api/v1/construction/projects`
- `POST /api/v1/construction/sites`
- `POST /api/v1/construction/tasks/from-command`
- `GET /api/v1/construction/dashboard`

Doctors office:

- `POST /api/v1/medical-office/tasks`
- `GET /api/v1/medical-office/dashboard`

## Channel Support

### Unified Channel Model

Every channel adapter must implement:

- Normalize inbound payload to `InboundMessage`.
- Resolve tenant, sender, and recipient identity.
- Send outbound message.
- Record provider response.
- Support retry-safe idempotency.
- Surface provider errors in `outbound_messages` and `reminder_attempts`.

### Telegram

Use cases:

- Staff task creation from direct chat or approved group.
- Internal reminders.
- Status updates through buttons or text replies.
- Optional customer reminders where customer has opted in.

Implementation details:

- Single webhook endpoint: `POST /api/v1/telegram/webhook`.
- Validate bot token and configured webhook secret.
- Map Telegram `chat_id` and `user_id` to `contact_channel_identities`.
- Support direct chat and group chat.
- Use inline buttons for common actions: complete, snooze, follow-up later, renewed, not interested.
- Store raw update in `inbound_messages.raw_payload`.

### WhatsApp

Use cases:

- Customer reminders.
- Worker reminders.
- Staff reminders where WhatsApp is preferred.
- Simple response capture.

Implementation details:

- Webhook endpoint: `POST /api/v1/whatsapp/webhook`.
- Verify Meta webhook challenge and signature.
- Store phone-number identity in E.164 format.
- Respect template-message rules for outbound business-initiated messages.
- Track opt-out replies such as STOP.
- Avoid PHI or sensitive details unless tenant policy explicitly allows the channel.

## Agent Design

### AI Orchestrator

Responsibilities:

- Classify domain and intent.
- Select specialized agent.
- Provide tenant context, actor role, available tools, and guardrail policy.
- Require structured output from agents.
- Validate output before tool execution.
- Record `agent_invocations`.

Required structured output:

```json
{
  "domain": "insurance",
  "intent": "create_policy_renewal_reminders",
  "confidence": 0.93,
  "entities": {},
  "proposed_actions": [],
  "missing_fields": [],
  "requires_human_approval": false,
  "sensitivity": "normal",
  "user_response": "I created the renewal reminder schedule."
}
```

### Agent Tool Boundary

Agents do not directly write arbitrary database records. They call approved application tools:

- `create_task`
- `update_task`
- `assign_task`
- `create_reminder`
- `cancel_reminders`
- `start_workflow`
- `send_message`
- `create_contact`
- `link_channel_identity`
- `create_insurance_policy`
- `create_insurance_lead`
- `create_construction_project`
- `create_construction_site`
- `create_medical_office_task`

Every tool must:

- Check tenant scope.
- Check actor permission.
- Validate input with Pydantic.
- Write audit events.
- Return structured results.

### Specialized Agents

Insurance Agent:

- Entity vocabulary: policy, premium, renewal, expiry, quote, demo, lead, carrier, agent.
- Workflows: policy renewal, premium reminder, lead/demo follow-up.
- Statuses: interested, renewed, not interested, follow-up later, expired.
- Reports: renewals due, expired policies, agent follow-ups, conversion.

Construction Agent:

- Entity vocabulary: project, site, worker, contractor, task, material, inspection, owner.
- Workflows: assign worker task, request completion proof, owner update, overdue escalation.
- Statuses: assigned, in progress, blocked, done, verified.
- Reports: overdue tasks, site progress, worker workload.

Doctors Office Agent:

- Entity vocabulary: appointment, patient, insurance verification, referral, billing, lab follow-up.
- Workflows: internal staff task, appointment-prep checklist, billing follow-up.
- Statuses: pending, ready, done, needs review.
- Reports: overdue office tasks, tomorrow prep, pending referrals.
- Guardrail: default to `phi_possible` when patient-specific content is detected.

General Task Agent:

- Handles normal task creation, reminders, summaries, and rescheduling.
- Routes to specialized agents when domain-specific terms are detected.

## Guardrails

### Tenant Isolation

- Every query must filter by `organization_id`.
- Tool calls must reject cross-tenant entity IDs.
- Webhooks must resolve tenant through configured channel connection, group mapping, phone number, or verified identity.

### Permissions

- Owners/admins configure agents, workflows, channels, and templates.
- Managers create and reassign tasks across their scope.
- Staff update their own tasks and create allowed tasks.
- External contacts can only respond to messages addressed to them.
- Platform support access must be audited and time-bounded.

### Human Approval

Require approval before:

- Sending a first message to a customer without verified consent.
- Sending sensitive medical/patient-related content over external channels.
- Sending bulk messages.
- Canceling or closing more than one task from an AI command.
- Changing tenant-level channel settings.

### Privacy and Compliance

- Store consent status for contacts.
- Support opt-out for WhatsApp and Telegram.
- Minimize PHI in doctors-office workflows.
- Mask sensitive fields in logs.
- Never include raw secrets in `channel_connections.config`.
- Store provider credentials in Secret Manager and keep only `secret_ref`.

### Prompt Injection and Untrusted Content

- Treat inbound customer/worker messages and attachments as untrusted.
- Do not allow inbound text to override system instructions.
- Tools must be permission-checked independently of model output.
- If an attachment asks the AI to ignore rules, log the event and continue with normal extraction only.

### Message Safety

- Generate messages from approved templates where possible.
- Show preview and require approval for sensitive outbound messages.
- Respect quiet hours and recipient timezone.
- Deduplicate reminders with `dedupe_key`.
- Retry failed attempts with capped backoff.

## Testing Strategy

Backend unit tests:

- Domain classification routes to correct agent.
- Tool validators reject missing fields and cross-tenant IDs.
- Reminder schedule generation creates the correct stages.
- Deduplication prevents duplicate reminders.
- Guardrails require approval for sensitive medical outbound messages.
- WhatsApp opt-out cancels future external reminders.

Backend integration tests:

- `POST /api/v1/tasks` creates task, assignment, audit event.
- Insurance policy renewal workflow creates five reminders.
- Renewal completion cancels remaining reminders.
- Telegram webhook normalizes inbound message and creates task through AI command.
- WhatsApp webhook verifies signature/challenge and captures replies.
- Celery reminder processor sends due messages and records attempts.

Frontend tests:

- Task list filters by status, domain, assignee, and due date.
- Agent command bar shows extracted action preview before execution when approval is required.
- Channel preference form validates Telegram/WhatsApp configuration.
- Insurance dashboard renders renewal and follow-up KPIs.
- Construction dashboard renders worker/site workload.
- Doctors-office dashboard hides sensitive details from unauthorized roles.

End-to-end tests:

- Owner configures Telegram and WhatsApp channel placeholders.
- Agent creates insurance policy and starts renewal workflow.
- Simulated reminder is sent through mocked WhatsApp adapter.
- Customer reply updates task/workflow state.
- Manager dashboard shows escalation after missed renewal.

## Phased Implementation

### MVP Boundary

Build the platform in a narrow but extensible order:

1. Core task, reminder, contact, channel, audit, approval, and agent-session foundation.
2. Telegram and WhatsApp channel adapters with mocked providers for tests.
3. General Task Agent and Insurance Agent only.
4. Insurance MVP UI: command box, renewals due, follow-up queue, needs approval, customer/policy detail.
5. Admin portal for onboarding and managing tenant customers.
6. Construction Agent and Doctors Office Agent after the insurance workflow is validated with real usage.

Do not build construction and doctors-office production workflows before the insurance workflow proves the shared platform.

### Phase 0: Project Foundation

- Set up backend/frontend using GyantrAI stack.
- Add environment config and Docker compose.
- Add auth/tenant baseline.
- Add CI for lint, typecheck, tests.

### Phase 1: Core Task Platform

- Database schema for tenants, users, contacts, tasks, assignments, reminders, messages, audit.
- CRUD APIs.
- Reminder scheduler with Celery.
- Dashboard shell and task workbench.

### Phase 2: Channel Framework

- Unified channel service.
- Telegram webhook and outbound adapter.
- WhatsApp webhook and outbound adapter.
- Channel preference and consent management.
- Mock adapters for automated tests.

### Phase 3: AI Orchestrator and Agents

- Agent registry.
- Domain and intent classification.
- Structured output validation.
- Tool execution layer.
- Guardrail checks and human approval flow.
- General Task Agent and Insurance Agent.

### Phase 4: Insurance MVP

- Insurance policy and lead tables.
- Renewal workflow.
- Demo/lead follow-up workflow.
- Insurance dashboard and reports.
- Telegram/WhatsApp reminder templates.

### Phase 5: Construction MVP

- Project/site records.
- Worker assignment workflows.
- Completion proof attachment support.
- Owner update workflow.
- Construction dashboard.

### Phase 6: Doctors Office MVP

- Privacy-sensitive task workflows.
- Staff-only reminders.
- Appointment prep and billing/referral follow-up tasks.
- Role-based redaction.
- Doctors-office dashboard.

### Phase 7: Production Hardening

- Observability dashboards.
- Replay tools for failed reminders.
- Rate limits.
- Data retention jobs.
- Security review.
- UAT scripts and runbooks.

## GitHub Issue Backlog

Use the issue files in `issues/` as implementation tickets:

- `001-EPIC-agentic-task-manager-platform.md`
- `002-TASK-project-foundation.md`
- `003-TASK-core-database-schema.md`
- `004-STORY-task-reminder-engine.md`
- `005-STORY-channel-framework-telegram-whatsapp.md`
- `006-STORY-ai-orchestrator-and-agent-registry.md`
- `007-STORY-insurance-agent-mvp.md`
- `008-STORY-construction-agent-mvp.md`
- `009-STORY-doctors-office-agent-mvp.md`
- `010-STORY-frontend-task-workbench-and-dashboards.md`
- `011-TASK-guardrails-observability-and-test-suite.md`
- `012-TASK-agent-contracts-registry-classifier.md`
- `013-STORY-general-task-agent.md`
- `014-STORY-insurance-specialized-agent.md`
- `015-STORY-construction-specialized-agent.md`
- `016-STORY-doctors-office-specialized-agent.md`
- `017-TASK-approval-sessions-templates-preferences.md`
- `018-STORY-admin-portal-customer-management.md`
- `019-TASK-database-migrations-and-github-pipelines.md`
