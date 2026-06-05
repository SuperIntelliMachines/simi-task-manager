---
title: "[ATM-001] [Epic] Agentic AI Task Manager Platform"
labels: [epic, platform, agentic-ai, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-001 - Epic: Agentic AI Task Manager Platform

## Objective

Build a reusable AI task-management platform where specialized business agents run on a shared task, workflow, reminder, messaging, permissions, and audit foundation.

## Scope

This epic includes:

- Project foundation using the GyantrAI stack.
- Core database schema.
- Task and reminder engine.
- Telegram and WhatsApp channel support.
- AI orchestrator and specialized agents.
- Insurance Agent MVP.
- Construction Agent MVP.
- Doctors Office Agent MVP.
- Frontend task workbench and dashboards.
- Guardrails, observability, and tests.

## Reference Spec

Read `docs/agentic-task-manager-platform-spec.md` before implementation.

## Child Issues

- ATM-002 Project Foundation
- ATM-003 Core Database Schema
- ATM-004 Task and Reminder Engine
- ATM-005 Telegram and WhatsApp Channel Framework
- ATM-006 AI Orchestrator and Agent Registry
- ATM-007 Insurance Agent MVP
- ATM-008 Construction Agent MVP
- ATM-009 Doctors Office Agent MVP
- ATM-010 Frontend Task Workbench and Dashboards
- ATM-011 Guardrails, Observability, and Test Suite

## Acceptance Criteria

- [ ] The system supports generic tasks, reminders, assignments, contacts, and audit events.
- [ ] Tenant owners can choose Telegram or WhatsApp as communication channels.
- [ ] AI commands route only to specialized agents enabled for the tenant.
- [ ] Insurance renewal workflow is production-ready for first customer.
- [ ] Construction and doctors-office verticals have working MVP flows.
- [ ] Automated tests cover core workflows and guardrails.
- [ ] All sensitive actions are permission-checked and audited.

## Validation

- Run backend tests with `pytest`.
- Run frontend tests with `npm run test`.
- Run frontend typecheck with `npm run typecheck`.
- Run at least one E2E smoke test for insurance renewal workflow.
