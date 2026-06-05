---
title: "[ATM-010] [Story] Frontend Task Workbench and Dashboards"
labels: [story, frontend, react, dashboards, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-010 - Frontend Task Workbench and Dashboards

## Objective

Build the web UI for owners, managers, and staff to manage tasks, channels, AI commands, vertical dashboards, approvals, and reports.

The UX should follow the established GyantrAI visual language and feel like a rich modern AI product, not a plain CRUD dashboard. Use the same frontend stack and design conventions as GyantrAI: React, TypeScript, Tailwind, Radix/shadcn-style components, lucide icons, polished state transitions, responsive layouts, and high-signal data surfaces.

## Implementation Steps

1. Establish GyantrAI-aligned design foundation:
   - reuse or mirror GyantrAI theme tokens, spacing, typography, component density, and interaction patterns
   - create a polished AI-era app shell with command-forward workflows
   - use shadcn/Radix-style primitives, lucide icons, subtle motion, skeleton loading states, empty states, and toast feedback
   - support responsive desktop/tablet/mobile layouts without visual breakage
   - avoid generic bootstrap-style tables or unfinished placeholder UI

2. Create app shell:
   - authenticated layout
   - tenant switcher placeholder if needed
   - navigation for Tasks, Agents, Channels, Insurance, Construction, Medical Office, Settings

3. Build task workbench:
   - filters: status, domain, assignee, due date, priority
   - task table/list
   - task detail drawer
   - assignment controls
   - complete/snooze/cancel actions
   - audit timeline

4. Build AI command bar:
   - natural language input
   - extracted action preview
   - confidence display
   - missing field prompts
   - approval-required state
   - execution result

5. Build channel settings:
   - Telegram connection card
   - WhatsApp connection card
   - test message action
   - contact preferred channel selector
   - consent status display

6. Build dashboards:
   - Insurance: due renewals, expired policies, pending follow-ups, conversion metrics
   - Construction: overdue tasks, site progress, worker workload, blocked tasks
   - Medical Office: overdue internal tasks, tomorrow prep, referrals/billing queues with redaction

7. Add frontend API clients and TanStack Query hooks.

8. Add validation with Zod and React Hook Form.

## Acceptance Criteria

- [ ] Manager can create and manage tasks from UI.
- [ ] AI command bar can submit command and show preview/result.
- [ ] UI matches the GyantrAI-style rich AI product experience, including polished interaction states, responsive layouts, and consistent design tokens.
- [ ] Channel settings allow Telegram/WhatsApp configuration placeholders.
- [ ] Insurance dashboard supports first customer workflow.
- [ ] Construction and medical office dashboards render MVP data.
- [ ] Unauthorized users do not see restricted details.

## Test Cases

- Task filters update API query parameters.
- Complete button calls correct mutation and updates cache.
- AI command preview displays approval state.
- App shell, command bar, dashboard cards, tables, drawers, loading states, and empty states visually follow the GyantrAI-aligned theme.
- Channel form validates required fields.
- Insurance dashboard handles loading, empty, and populated states.
- Medical office dashboard redacts sensitive fields for viewer role.

## Validation

```bash
cd frontend
npm run typecheck
npm run test
npm run build
npm run test:e2e -- --grep "task workbench"
```
