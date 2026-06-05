# Simi Task Manager

Simi Task Manager is an agentic AI task-management platform for small and medium businesses. It combines a generic task, reminder, workflow, and messaging engine with specialized line-of-business agents.

The first production vertical is an Insurance Agent assistant for policy renewals, premium reminders, lead follow-ups, demo follow-ups, and agent escalation. The platform is designed to later support construction teams, doctors' offices, and other service businesses through specialized agents on the same foundation.

## Product Direction

Simi is not a one-off reminder bot. It is:

> A generic AI task manager powered by specialized business agents.

The platform owns the reusable primitives:

- Tasks, assignments, reminders, statuses, comments, and audit events
- Contacts, users, roles, tenants, and notification preferences
- Telegram and WhatsApp communication channels
- Workflow templates and scheduled jobs
- AI orchestration, tool execution, clarifications, and approvals
- Guardrails for consent, tenant isolation, sensitive data, and duplicate sends
- Admin portal for onboarding and managing customer tenants

Specialized agents add domain intelligence:

- Insurance Agent: policies, premiums, renewals, quotes, demos, leads
- Construction Agent: projects, sites, workers, work orders, completion proof, owner updates
- Doctors Office Agent: appointment prep, insurance verification, referrals, billing follow-up, privacy-aware staff tasks
- General Task Agent: normal reminders, assignments, follow-ups, and task summaries

## MVP Scope

The recommended build order is intentionally narrow:

1. Core task, reminder, contact, channel, audit, approval, and agent-session foundation
2. Telegram and WhatsApp adapters with mocked providers for tests
3. General Task Agent and Insurance Agent
4. Insurance MVP UI: command box, renewals due, follow-up queue, needs approval, customer/policy detail
5. Admin portal for onboarding and managing tenants
6. Construction and doctors-office agents after the insurance workflow is validated with real usage

## Reference Stack

The implementation should follow the same stack pattern as GyantrAI:

- Backend: Python 3.11, FastAPI, Pydantic, SQLAlchemy async, Alembic, PostgreSQL, Redis, Celery
- AI: LangChain-compatible provider layer with OpenAI/Anthropic support
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, Radix/shadcn-style components, TanStack Query
- Testing: pytest, pytest-asyncio, pytest-cov, Vitest, React Testing Library, MSW, Playwright
- Deployment: Docker, Cloud Run or equivalent, Cloud SQL PostgreSQL, Redis/Memorystore, Secret Manager

Frontend UX should follow the established GyantrAI product style: rich AI-era interfaces, polished command surfaces, responsive layouts, high-signal dashboards, refined loading/empty/error states, and consistent Tailwind/Radix/shadcn-style components.

## Documentation

Start here:

- [Agentic Task Manager Platform Spec](docs/agentic-task-manager-platform-spec.md)
- [Specialized Agents Implementation Guide](docs/specialized-agents-implementation.md)
- [Admin Portal Design](docs/admin-portal-design.md)
- [Database Migrations and Deployment Pipelines](docs/database-migrations-and-deployment.md)
- [External Task Lifecycle Management](docs/external-task-lifecycle-management.md)
- [Original Insurance Reminder Bot Plan](Insurance-agent.md)

## Implementation Backlog

The `issues/` folder contains GitHub-issue-ready Markdown files. Each issue includes implementation steps, acceptance criteria, test cases, and validation commands.

Core platform:

- [ATM-001 Epic: Agentic AI Task Manager Platform](issues/001-EPIC-agentic-task-manager-platform.md)
- [ATM-002 Project Foundation](issues/002-TASK-project-foundation.md)
- [ATM-003 Core Database Schema](issues/003-TASK-core-database-schema.md)
- [ATM-004 Task, Workflow, and Reminder Engine](issues/004-STORY-task-reminder-engine.md)
- [ATM-005 Telegram and WhatsApp Channel Framework](issues/005-STORY-channel-framework-telegram-whatsapp.md)
- [ATM-006 AI Orchestrator and Agent Registry](issues/006-STORY-ai-orchestrator-and-agent-registry.md)

Vertical MVPs:

- [ATM-007 Insurance Agent MVP](issues/007-STORY-insurance-agent-mvp.md)
- [ATM-008 Construction Agent MVP](issues/008-STORY-construction-agent-mvp.md)
- [ATM-009 Doctors Office Agent MVP](issues/009-STORY-doctors-office-agent-mvp.md)
- [ATM-010 Frontend Task Workbench and Dashboards](issues/010-STORY-frontend-task-workbench-and-dashboards.md)

Hardening and specialized agents:

- [ATM-011 Guardrails, Observability, and Test Suite](issues/011-TASK-guardrails-observability-and-test-suite.md)
- [ATM-012 Agent Contracts, Registry, and Classifier](issues/012-TASK-agent-contracts-registry-classifier.md)
- [ATM-013 General Task Agent](issues/013-STORY-general-task-agent.md)
- [ATM-014 Insurance Specialized Agent](issues/014-STORY-insurance-specialized-agent.md)
- [ATM-015 Construction Specialized Agent](issues/015-STORY-construction-specialized-agent.md)
- [ATM-016 Doctors Office Specialized Agent](issues/016-STORY-doctors-office-specialized-agent.md)
- [ATM-017 Approval, Sessions, Templates, and Preferences](issues/017-TASK-approval-sessions-templates-preferences.md)
- [ATM-018 Admin Portal for Customer Management](issues/018-STORY-admin-portal-customer-management.md)
- [ATM-019 Database Migrations and GitHub Pipelines](issues/019-TASK-database-migrations-and-github-pipelines.md)
- [ATM-020 External Task Lifecycle Management](issues/020-STORY-external-task-lifecycle-management.md)

## Insurance MVP Capabilities

The Insurance Agent should support:

- Creating policies from natural language
- Tracking policyholder, policy type, carrier, policy number, premium, expiry date, assigned agent, and preferred channel
- Sending renewal reminders at expiry -10, -5, -2, 0, and +1 days
- Skipping reminder stages already in the past
- Canceling future reminders when a policy is renewed
- Escalating missed renewals to the assigned agent
- Logging demos and creating follow-up reminders
- Marking leads as interested, not interested, renewed, or follow-up later
- Summarizing due renewals, expired policies, and pending follow-ups

## Guardrails

The platform must enforce:

- Tenant isolation on every query and tool call
- Role-based permissions
- Customer consent and opt-out handling
- WhatsApp template rules for business-initiated messages
- Telegram/WhatsApp identity verification
- Approval for sensitive, bulk, or externally visible AI actions
- Audit events for task, reminder, message, approval, admin, and support actions
- Idempotent reminder processing and replay

## External Task Lifecycle

Simi is designed to later manage tasks originating from other applications without disturbing native tasks or existing insurance customers.

Examples:

- XChainGen order placed -> fulfillment task
- XChainGen payment failed -> customer follow-up task
- Food order delayed -> kitchen/manager escalation
- GyantrAI purchase order pending approval -> approval task
- GyantrAI vendor invoice received -> accountant review task

The source application remains the system of record for its business object. Simi owns task assignment, reminders, escalation, messaging, and task audit.

See [External Task Lifecycle Management](docs/external-task-lifecycle-management.md).

## Admin Portal

The admin portal manages:

- Customer tenants
- Tenant onboarding
- Users and roles
- Enabled agents and workflows
- Telegram and WhatsApp channel configuration
- Message templates
- Notification preferences
- Approval requests
- Failed reminders and safe replay
- Support access sessions
- Customer health, usage, and audit logs

## Development Approach

Use the issue files as the source of truth for implementation. A good first development sequence is:

1. ATM-002 Project Foundation
2. ATM-003 Core Database Schema
3. ATM-017 Approval, Sessions, Templates, and Preferences
4. ATM-004 Task, Workflow, and Reminder Engine
5. ATM-005 Telegram and WhatsApp Channel Framework
6. ATM-012 Agent Contracts, Registry, and Classifier
7. ATM-013 General Task Agent
8. ATM-014 Insurance Specialized Agent
9. ATM-007 Insurance Agent MVP
10. ATM-010 Frontend Task Workbench and Dashboards
11. ATM-018 Admin Portal
12. ATM-019 Database Migrations and GitHub Pipelines
13. ATM-020 External Task Lifecycle Management
14. ATM-011 Guardrails, Observability, and Test Suite

## CI/CD and Migrations

The repository includes workflow templates for:

- SQL migration validation and application
- Cloud SQL Auth Proxy database access
- Cloud Run development deployment
- Cloud Run staging/production deployment

See [Database Migrations and Deployment Pipelines](docs/database-migrations-and-deployment.md).

## Repository Status

This repository currently contains planning, architecture, and issue-ready implementation documents. Application code should be added according to the backlog and reference stack above.
