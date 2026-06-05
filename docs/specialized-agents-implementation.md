# Specialized Agents Implementation Guide

## Goal

Build specialized business agents that convert user intent into safe, validated task-management actions. Each agent understands one line of business, but all agents use the same orchestrator, guardrails, tool layer, database, and audit system.

This guide expands the agent layer from `docs/agentic-task-manager-platform-spec.md`.

## Agent Principles

- Agents do not directly write to the database.
- Agents return structured plans and call approved tools only through the orchestrator.
- Every tool call validates tenant scope, actor permissions, required fields, and sensitivity.
- Agents must ask clarification when required business fields are missing.
- Agents must require approval before sensitive or bulk external communication.
- Agents should generate concise confirmations and message drafts, not free-form operational changes.

## Runtime Components

```text
Inbound Command
      |
      v
AI Orchestrator
      |
      +--> Tenant Agent Router
      |
      +--> Guardrail Precheck
      |
      +--> Agent Registry
              |
              +--> General Task Agent
              +--> Insurance Agent
              +--> Construction Agent
              +--> Doctors Office Agent
      |
      +--> Structured Output Validator
      |
      +--> Tool Executor
      |
      +--> Audit Logger
      |
      v
User Confirmation / Approval Request / Clarification
```

## Agent Registry

Each agent definition should be stored in `agent_definitions` and mirrored in code.

Agent metadata:

- `key`: stable machine name.
- `name`: human display name.
- `domain`: `general`, `insurance`, `construction`, or `doctors_office`.
- `description`: what the agent handles.
- `system_prompt`: domain operating instructions.
- `tool_policy`: allowed tools and constraints.
- `guardrail_policy`: sensitivity, approval, and channel rules.
- `status`: active/inactive.

Recommended keys:

- `general_task_agent`
- `insurance_agent`
- `construction_agent`
- `doctors_office_agent`

Tenant assignment:

- Specialized agents are enabled per tenant during onboarding.
- Tenant agent assignment is stored in `organization_agent_configs`.
- A tenant normally has one primary specialized agent, for example an insurance agency tenant uses `insurance_agent`.
- Inbound WhatsApp, Telegram, or web messages first resolve the tenant, then load that tenant's enabled agents.
- Message text must not route work to a specialized agent that is not enabled for the tenant.
- The General Task Agent can be enabled for generic reminders, but it cannot escape tenant agent configuration and route into a disabled vertical.

## Orchestrator Contract

### Input

```json
{
  "organization_id": "uuid",
  "actor_user_id": "uuid",
  "source": "web|telegram|whatsapp",
  "text": "Remind Ravi about his policy renewal next Friday",
  "channel_context": {
    "channel": "telegram",
    "chat_id": "12345",
    "message_id": "abc"
  },
  "attachments": []
}
```

### Output

```json
{
  "status": "executed|needs_clarification|needs_approval|rejected|failed",
  "domain": "insurance",
  "intent": "create_renewal_reminder",
  "agent_key": "insurance_agent",
  "confidence": 0.91,
  "summary": "Created a renewal reminder for Ravi.",
  "created_entities": [
    {
      "type": "task",
      "id": "uuid"
    }
  ],
  "missing_fields": [],
  "approval_request_id": null,
  "user_message": "I created the renewal reminder for Ravi for next Friday."
}
```

## Agent Structured Response Schema

Agents must produce this shape before tools execute.

```json
{
  "domain": "insurance",
  "intent": "create_policy_renewal_workflow",
  "confidence": 0.94,
  "sensitivity": "normal",
  "entities": {
    "contact": {
      "name": "Ravi Kumar",
      "phone_e164": "+16025550123"
    },
    "policy": {
      "policy_type": "auto",
      "expiry_date": "2026-06-25",
      "premium_amount": 250.00,
      "currency": "USD"
    }
  },
  "missing_fields": [],
  "proposed_actions": [
    {
      "tool": "create_or_update_contact",
      "arguments": {}
    },
    {
      "tool": "create_insurance_policy",
      "arguments": {}
    },
    {
      "tool": "start_insurance_renewal_workflow",
      "arguments": {}
    }
  ],
  "requires_human_approval": false,
  "approval_reason": null,
  "clarifying_question": null,
  "user_response": "I can create the policy and schedule renewal reminders."
}
```

## Tenant Agent Router and Scoped Classifier

The router decides which tenant-enabled agent handles a command. The classifier is scoped by tenant configuration; it never chooses from the full global list of platform agents unless those agents are enabled for that tenant.

Routing behavior:

- If the tenant has one primary specialized agent, route normal user commands to that agent.
- If the tenant also has General Task Agent enabled, allow generic task intents to stay generic when they do not require vertical tools.
- If the tenant has multiple specialized agents enabled, classify only among those enabled agents.
- If the command appears to require a disabled domain, ask clarification or reject with a clear explanation.
- If a clarification session exists, resume the same agent that created the session.

Insurance indicators:

- policy, premium, renewal, expiry, coverage, claim, quote, demo, lead, carrier, insured, policyholder

Construction indicators:

- site, worker, contractor, wiring, plumbing, concrete, material, inspection, project, owner update, completion photo

Doctors office indicators:

- patient, appointment, referral, lab, billing, insurance verification, front desk, medical record, prescription, clinic

General task indicators:

- remind, assign, follow up, schedule, complete, todo, task, call, email without strong vertical context

Scoped classifier behavior:

- If a vertical confidence is high and that agent is enabled for the tenant, route to that agent.
- If two enabled domains are plausible, ask one clarification.
- If no enabled specialized domain is strong and General Task Agent is enabled, route to General Task Agent.
- If no enabled agent can handle the command safely, ask clarification or reject.
- Patient-specific content may route to Doctors Office Agent only when that agent is enabled for the tenant; otherwise reject or escalate for admin configuration review.

## Shared Tools

All tools must use Pydantic input schemas and return structured results.

### create_task

Creates a generic task.

Required:

- `organization_id`
- `title`
- `domain`

Optional:

- `description`
- `due_at`
- `priority`
- `primary_contact_id`
- `sensitivity`
- `metadata`

Validation:

- Actor must have task creation permission.
- `organization_id` must match actor membership.
- `due_at` must include timezone or be resolved using tenant timezone.

### assign_task

Assigns task to user or contact.

Validation:

- Task and assignee must belong to same tenant.
- Staff can assign only within allowed scope.
- External contact assignment requires allowed workflow.

### create_reminder

Creates a reminder for a task or workflow.

Validation:

- Recipient must have a valid channel identity for selected channel or a pending setup state.
- External contact must have consent unless reminder is internal-only or legally allowed by tenant policy.
- Deduplication key must be deterministic.

### send_message

Queues outbound message through channel service.

Validation:

- Sensitive messages may require approval.
- External messages must respect consent, quiet hours, and opt-out.
- WhatsApp business-initiated messages must use approved template keys.

### start_workflow

Starts a workflow from a template.

Validation:

- Template must be active.
- Required workflow fields must be present.
- Actor must have permission for the workflow domain.

## Specialized Agents

## General Task Agent

### Purpose

Handle generic reminders, follow-ups, assignments, rescheduling, summaries, and task updates when no vertical-specific agent is needed.

### Intents

- `create_task`
- `create_reminder`
- `assign_task`
- `complete_task`
- `snooze_task`
- `summarize_tasks`
- `list_overdue_tasks`
- `reschedule_task`

### Required Fields by Intent

`create_task`:

- title or inferred action

`create_reminder`:

- recipient
- reminder time
- message intent

`assign_task`:

- assignee
- task/action

### Clarification Examples

- "Who should I assign this to?"
- "When should I remind them?"
- "Is this for a customer or an internal team member?"

### Example Commands

- "Remind me to call Suresh tomorrow morning."
- "Assign Priya to submit the report by Friday."
- "Show me overdue tasks for this week."

## Insurance Agent

### Purpose

Manage insurance workflows for policy renewals, premium reminders, lead follow-ups, demo follow-ups, and agent escalation.

### Domain Entities

- policyholder
- policy
- premium
- renewal
- lead
- demo
- agent
- carrier

### Intents

- `create_policy`
- `create_policy_renewal_workflow`
- `create_premium_reminder`
- `log_demo`
- `create_lead_followup`
- `mark_policy_renewed`
- `mark_lead_not_interested`
- `reschedule_followup`
- `summarize_renewals`
- `summarize_agent_followups`

### Required Fields by Intent

`create_policy`:

- policyholder
- policy type
- expiry date

Optional but recommended:

- premium amount
- carrier
- policy number
- preferred channel
- assigned agent

`create_policy_renewal_workflow`:

- policy
- expiry date
- policyholder recipient
- selected channel

`log_demo`:

- lead/contact
- demo date
- assigned agent

`create_lead_followup`:

- lead/contact
- follow-up date or rule
- assigned agent

### Workflow Rules

Policy renewal workflow:

- Create reminder stages at expiry -10, -5, -2, 0, and +1.
- Skip stages already in the past.
- Use contact preferred channel.
- Copy assigned agent only if configured.
- Cancel future stages when policy is marked renewed.
- Create escalation task for assigned agent if not renewed by expiry +1.

Lead follow-up workflow:

- Trigger from demo logged or direct follow-up command.
- Remind assigned agent after configured X days.
- Close cycle when marked not interested.
- Reschedule when marked follow-up later.

### Message Templates

Customer renewal - before expiry:

```text
Hi {customer_name}, your {policy_type} policy expires on {expiry_date}. Please renew before the due date to avoid a coverage gap.
```

Customer renewal - expired:

```text
Hi {customer_name}, your {policy_type} policy expired on {expiry_date}. Please contact {agent_name} to renew.
```

Agent follow-up:

```text
Follow up with {customer_name} about the {policy_type} plan decision.
```

### Guardrails

- Do not promise coverage, pricing, or claim approval unless present in approved business data.
- Do not send policy details to an unverified channel identity.
- Require approval for bulk renewal campaigns.
- Respect opt-out and consent.

### Example Commands

- "Create a car policy for Ravi expiring June 25 and remind him on WhatsApp."
- "Log a demo for Priya today and remind me in 3 days."
- "Mark Kumar's policy renewed."
- "Show policies expiring in the next 10 days."

## Construction Agent

### Purpose

Manage project/site work assignment, worker reminders, task status capture, completion proof, manager escalation, and owner updates.

### Domain Entities

- project
- site
- worker
- contractor
- owner
- work order
- material
- inspection
- completion proof

### Intents

- `create_project`
- `create_site`
- `assign_worker_task`
- `request_completion_update`
- `mark_task_done`
- `mark_task_blocked`
- `request_completion_photo`
- `create_owner_update`
- `summarize_site_progress`
- `summarize_worker_workload`

### Required Fields by Intent

`assign_worker_task`:

- worker
- work item
- site or project
- due date

`create_owner_update`:

- project or site
- summary period
- owner recipient

### Workflow Rules

Worker task workflow:

- Create task assigned to worker.
- Send reminder through worker preferred channel.
- Ask for done/blocked response.
- If done and proof required, request photo or note.
- Escalate overdue work to manager.

Owner update workflow:

- Summarize completed, blocked, and overdue tasks.
- Draft owner-facing message.
- Require manager approval before sending.

### Message Templates

Worker task:

```text
Task: {task_title}. Site: {site_name}. Due: {due_date}. Reply Done or Blocked.
```

Manager escalation:

```text
{worker_name}'s task is overdue: {task_title} at {site_name}.
```

Owner update:

```text
Project update for {project_name}: {summary}
```

### Guardrails

- Do not send internal cost, worker performance, or dispute details to owners unless approved.
- Require approval for owner updates.
- Do not mark task complete from ambiguous replies.
- Treat uploaded photos as attachments linked to task, not proof of quality unless manager verifies.

### Example Commands

- "Assign Ravi to finish wiring at Site A by tomorrow."
- "Ask all workers at Site B for today's status."
- "Update the owner when plumbing is complete."
- "Show blocked tasks for Project Phoenix."

## Doctors Office Agent

### Purpose

Manage privacy-aware internal office tasks for appointment prep, insurance verification, referrals, billing follow-up, and staff reminders.

### Domain Entities

- patient
- appointment
- staff
- front desk
- insurance verification
- referral
- billing
- lab follow-up

### Intents

- `create_appointment_prep_task`
- `create_insurance_verification_task`
- `create_referral_followup_task`
- `create_billing_followup_task`
- `assign_staff_task`
- `summarize_office_tasks`
- `list_overdue_sensitive_tasks`

### Required Fields by Intent

`create_appointment_prep_task`:

- appointment date/time
- staff assignee or team
- minimal patient reference

`create_insurance_verification_task`:

- appointment or patient reference
- due date
- assignee

`create_referral_followup_task`:

- patient reference
- referral target or context
- due date

### Workflow Rules

- Patient-specific commands default to `phi_possible`.
- Use internal reminders by default.
- External patient messaging requires approval and allowed channel policy.
- Redact patient-sensitive fields for unauthorized viewers.
- Log sensitive context access.

### Message Templates

Internal insurance verification:

```text
Verify insurance for {patient_reference}'s appointment on {appointment_time}.
```

Internal referral follow-up:

```text
Follow up on referral for {patient_reference}. Due: {due_date}.
```

### Guardrails

- Do not send clinical details externally.
- Do not include diagnosis, treatment, medication, or lab details in external reminders unless explicitly approved by tenant policy.
- Ask clarification when patient identity is ambiguous.
- Prefer staff-only reminders.

### Example Commands

- "Remind front desk to verify insurance for tomorrow's 10 AM appointment."
- "Create a referral follow-up task for Maria due Friday."
- "Show overdue billing follow-ups."

## Approval Flow

Agents should return `needs_approval` when a proposed action is valid but not safe to execute automatically.

Approval examples:

- Bulk customer reminders.
- Owner updates in construction.
- Patient-specific external messages.
- First outbound customer message without verified consent.
- Closing multiple tasks from a single AI command.

Approval request fields:

- requester
- agent
- proposed actions
- message preview
- sensitivity
- approval reason
- expires_at

## Clarification Flow

Agents should return `needs_clarification` when required fields are missing or ambiguous.

Clarification rules:

- Ask one clear question at a time.
- Preserve extracted fields in pending context.
- Resume the same agent after user answers.
- Expire stale clarification state after a configured period.

Examples:

- "Which Ravi do you mean?"
- "What date should I use for the policy expiry?"
- "Should this reminder go by Telegram or WhatsApp?"

## Testing Matrix

### Tenant Router and Classifier Tests

- Insurance tenant command routes to the tenant-enabled Insurance Agent.
- Construction tenant command routes to the tenant-enabled Construction Agent.
- Patient command routes to Doctors Office Agent only for a tenant where that agent is enabled.
- Generic reminder routes to General Task Agent when enabled for the tenant.
- Disabled-domain command does not route to a globally registered agent.
- Ambiguous command asks clarification.

### Agent Unit Tests

- Agent extracts required entities.
- Missing required fields produce clarification.
- Low confidence does not execute tools.
- Sensitive actions require approval.
- Structured output validates against schema.

### Tool Execution Tests

- Tool rejects cross-tenant IDs.
- Tool rejects unauthorized actor.
- Tool writes audit event.
- Tool returns deterministic result.

### End-to-End Agent Tests

- Insurance: create policy renewal workflow from natural language.
- Construction: assign worker task and capture done reply.
- Doctors Office: create privacy-sensitive staff task and redact for viewer.
- General: create reminder and snooze from follow-up command.

## Initial Build Order

1. Shared agent contracts and fake LLM provider.
2. Agent registry, tenant agent router, and scoped classifier.
3. Tool executor with permission and tenant checks.
4. General Task Agent.
5. Insurance Agent.
6. Construction Agent.
7. Doctors Office Agent.
8. Approval and clarification persistence.
9. Full regression test suite.
