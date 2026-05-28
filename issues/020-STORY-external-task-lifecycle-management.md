---
title: "[ATM-020] [Story] External Task Lifecycle Management"
labels: [story, integrations, external-tasks, platform, P1]
milestone: "Post Insurance MVP"
assignees: ""
---

# ATM-020 - External Task Lifecycle Management

## Objective

Add support for managing the lifecycle of tasks originating from external applications such as XChainGen, GyantrAI, ecommerce systems, food-business systems, ERP modules, CRM systems, and custom apps.

This issue is intentionally deferred until after the Insurance MVP, but the schema support should be included early to avoid disruptive changes later.

## Reference

Read:

- `docs/external-task-lifecycle-management.md`
- `docs/agentic-task-manager-platform-spec.md`

## Implementation Steps

1. Add database tables:
   - `external_applications`
   - `external_task_links`
   - `external_task_events`
   - `external_status_mappings`
   - `webhook_subscriptions`

2. Extend `tasks`:
   - add nullable `external_task_link_id`
   - ensure source can identify external tasks
   - add indexes for external task lookup

3. Implement external application service:
   - register application
   - rotate API credentials
   - enable/disable application
   - configure callback URL
   - configure allowed event types

4. Implement inbound event API:
   - `POST /api/v1/external/tasks/events`
   - authenticate source application
   - validate idempotency key
   - store raw event payload
   - create/update external task link
   - create/update Simi task
   - write audit events

5. Implement status mapping:
   - map external status to Simi status
   - support tenant/app-specific overrides
   - reject unknown statuses unless fallback is configured

6. Implement outbound sync:
   - detect Simi task status changes for linked external tasks
   - create outbound external task event
   - deliver webhook callback
   - retry failed callbacks with capped backoff
   - avoid duplicate callbacks with idempotency

7. Implement admin UI:
   - external applications list
   - external application detail
   - status mappings
   - webhook subscriptions
   - event log
   - retry failed sync

8. Add first adapter tests:
   - XChainGen order fulfillment task
   - XChainGen food order delay escalation
   - GyantrAI purchase order approval task
   - GyantrAI vendor invoice review task

## Acceptance Criteria

- [ ] External app can create a Simi task through lifecycle event API.
- [ ] Repeated event with same idempotency key does not duplicate task.
- [ ] External task link preserves source app, external task ID, object type, and object ID.
- [ ] Simi status changes can be sent back through outbound callback.
- [ ] Failed callbacks are retryable and audited.
- [ ] Admin can view external task events and mappings.
- [ ] Existing native tasks and insurance workflows continue to work unchanged.

## Test Cases

- `task.created` from XChainGen creates one Simi task.
- Duplicate `task.created` returns previous task/link.
- `task.completed` from external app completes linked Simi task.
- Simi task completion sends outbound callback when bidirectional sync is enabled.
- Unknown external status is rejected when no mapping exists.
- Disabled external application cannot send events.
- Cross-tenant external task link is rejected.

## Validation

```bash
cd backend
python -m pytest tests/unit/external/test_external_task_service.py -v
python -m pytest tests/unit/external/test_status_mapping.py -v
python -m pytest tests/integration/test_external_task_events_api.py -v
python -m pytest tests/integration/test_external_task_outbound_sync.py -v
```

