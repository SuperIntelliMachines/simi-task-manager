# External Task Lifecycle Management

## Purpose

Simi Task Manager should be able to manage tasks that originate from other applications, including XChainGen, GyantrAI, ecommerce systems, food-business systems, ERP modules, CRM systems, and custom applications.

The goal is to support this in the data model now while deferring implementation until after the core Insurance MVP is stable.

## Product Principle

Simi should be the task lifecycle and reminder brain. The external application remains the system of record for its business object.

Examples:

- XChainGen owns orders, carts, payments, and stores.
- GyantrAI owns ERP objects such as purchase orders, invoices, tenders, and material requests.
- Simi owns task assignment, reminders, escalation, agent workflows, messaging, and task audit.

## Architecture

```text
External Application
        |
        | task.created / task.updated / task.completed
        v
External Task Gateway
        |
        v
Idempotency + Auth + Status Mapping
        |
        v
Simi Task Engine
        |
        +--> Reminders
        +--> Agents
        +--> Telegram / WhatsApp
        +--> Audit Events
        |
        v
Outbound Webhook Callback
```

## Example Integrations

### XChainGen Ecommerce

Events:

- order placed
- order delayed
- payment failed
- refund requested
- delivery not assigned
- customer support request

Simi tasks:

- fulfillment task
- customer follow-up
- refund review
- delivery escalation
- manager alert

### Food Business Product

Events:

- food order received
- kitchen prep delayed
- delivery driver unavailable
- customer complaint
- refund requested

Simi tasks:

- kitchen prep task
- manager escalation
- customer notification approval
- delivery dispatch follow-up

### GyantrAI ERP

Events:

- purchase order pending approval
- vendor invoice received
- payment approval needed
- material shortage detected
- tender deadline approaching
- document extraction failed

Simi tasks:

- approval task
- accountant review task
- vendor follow-up
- manager escalation
- bid preparation reminder

## Inbound Event Contract

Endpoint:

```text
POST /api/v1/external/tasks/events
```

Request:

```json
{
  "source_app": "xchaingen",
  "idempotency_key": "xchaingen:order:12345:task.created:v1",
  "external_event_id": "evt_abc123",
  "external_task_id": "order_12345_fulfillment",
  "external_object_type": "order",
  "external_object_id": "12345",
  "event_type": "task.created",
  "title": "Prepare order #12345",
  "description": "Kitchen prep required",
  "assignee_ref": "kitchen_team",
  "due_at": "2026-05-28T18:30:00Z",
  "priority": "high",
  "domain": "food_ops",
  "external_url": "https://xchaingen.example/orders/12345",
  "metadata": {
    "store_id": "phoenix-01",
    "customer_name": "Ravi",
    "order_total": 42.50
  }
}
```

Response:

```json
{
  "status": "processed",
  "task_id": "uuid",
  "external_task_link_id": "uuid",
  "event_id": "uuid"
}
```

## Status Mapping

Default mapping:

```text
External Status      Simi Status
new                  open
assigned             in_progress
waiting_customer     waiting
done                 completed
canceled             canceled
failed               failed
```

Each tenant and application can override this mapping.

## Outbound Callback Contract

When Simi task state changes, Simi can notify the source app.

Example callback:

```json
{
  "event_type": "simi.task.completed",
  "external_task_id": "order_12345_fulfillment",
  "simi_task_id": "uuid",
  "simi_status": "completed",
  "completed_at": "2026-05-28T18:12:00Z",
  "completed_by": {
    "type": "user",
    "display_name": "Kitchen Manager"
  },
  "metadata": {
    "completion_note": "Order ready for dispatch"
  }
}
```

## Database Tables

The platform spec includes these tables:

- `external_applications`
- `external_task_links`
- `external_task_events`
- `external_status_mappings`
- `webhook_subscriptions`

These tables should be added to the early schema so future integrations do not require disruptive changes to the core task model.

## Guardrails

- External applications must authenticate.
- API keys and webhook secrets must be stored by secret reference, not plaintext.
- Events must include idempotency keys.
- Cross-tenant external task IDs must be rejected.
- External payloads are untrusted input.
- Simi must not overwrite external business objects unless an explicit outbound sync policy allows it.
- Outbound callbacks must be retried safely and never duplicated without idempotency.

## Deferred Implementation Plan

Implement later, after:

1. Core task engine.
2. Reminder engine.
3. Channel framework.
4. General Task Agent.
5. Insurance Agent MVP.
6. Admin portal baseline.

First concrete adapters:

1. XChainGen ecommerce/food task adapter.
2. GyantrAI ERP task adapter.

