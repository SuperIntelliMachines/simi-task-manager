# Generic Reminder Engine

The reminder engine is module-independent. Configuration lives in `reminder_configs`;
execution uses registered entity resolvers and generic generator/processor services.

## Architecture

```
User → Reminder Settings UI → reminder_configs
          ↓
Generic scheduler (reminder_engine_jobs)
          ↓
ReminderGeneratorService → ReminderResolverFactory → *Resolver
          ↓
reminder_instances
          ↓
ReminderProcessorService → ChannelService
```

## Adding a new module (e.g. Pest Control)

1. Create `app/services/reminder_resolvers/pest_control_resolver.py`
2. Decorate with `@register_resolver("pest_control")`
3. Implement `metadata()` (triggers, workflow events, recipient types, channels, default template)
4. Expose **Reminder Settings** in the UI and save via `PUT /api/v1/reminders/config/settings`

No changes are required to the generator, processor, factory resolve path, or scheduler.
Reminder Management discovers the module automatically via `GET /reminders/modules`.

### Registered modules

| entity_type | Resolver | Data source |
|-------------|----------|-------------|
| `policy` | `PolicyReminderResolver` | SIMI insurance policies (local DB) |
| `claims` | `ClaimsReminderResolver` | Gyantr AI Service Cases via `ClaimsClient` (no local Claims tables) |

`ClaimsReminderResolver` is Phase 2A architecture only: it can fetch/map a Service Case,
but reminder business rules (24h intake / 48h escalation / return-pending) wait on
Claims lifecycle API fields (`submitted_at` / `status_changed_at`, etc.).

## Channels

Supported reminder channels:

- `whatsapp`
- `telegram`
- `email`
- `sms` (mock)
- `in_app` — creates rows in the generic `notifications` inbox via `InAppAdapter`

For `in_app`, resolvers must populate `ReminderEntitySnapshot.recipient_user_id`.
Phone-based channels continue to use `recipient`.

## Reminder configuration (UI-driven)

Users configure reminders per entity through the common API:

- `GET /api/v1/reminders/modules` — registered modules (from resolvers' `metadata()`)
- `GET /api/v1/reminders/modules/{module}/schema` — triggers, recipients, channels, default template
- `GET /api/v1/reminders/channels` — platform channels from `ChannelService`
- `GET /api/v1/reminders/templates` — lightweight template catalog
- `GET /api/v1/reminders/entity-types` — registered resolver types (keys only)
- `GET /api/v1/reminders/config/{entity_type}/{entity_id}?organization_id=` — list active configs
- `PUT /api/v1/reminders/config/settings` — upsert full schedule (channels × offsets), deactivate stale rows
- `POST /api/v1/reminders/config` — legacy create (single channel, int offsets)
- `PATCH /api/v1/reminders/config/{id}` — update one row
- `DELETE /api/v1/reminders/config/{id}` — deactivate one row

Example settings body:

```json
{
  "organization_id": 607,
  "entity_type": "policy",
  "entity_id": 120,
  "channels": ["whatsapp"],
  "offsets": [
    {"offset_value": 30, "offset_unit": "days"},
    {"offset_value": 7, "offset_unit": "days"}
  ],
  "template_key": "policy_renewal_reminder",
  "entity_label": "Health Renewal",
  "sender_name": "ABC Insurance",
  "dnd_start": "22:00",
  "dnd_end": "08:00"
}
```

Insurance (and other domain modules) must **not** create `reminder_configs` on entity create/update.

## Scheduler (generic)

Internal jobs use `app/jobs/reminder_engine_jobs.py`:

- `generate_reminder_instances(session, organization_id=None)` — reads active `reminder_configs`, uses resolvers
- `process_due_reminder_instances(session, organization_id)` — sends due `reminder_instances`
- `run_reminder_engine_cycle(session)` — generate then process

Scheduler HTTP API (`/api/v1/internal/reminders/generate-all`, `/process`) uses the same services.

## Legacy insurance sync

`app/services/policy_legacy_reminder_sync.py` remains for one-off migration/repair only (`/internal/jobs/repair-policy-reminders`). New deployments should use the Reminder Settings UI.

## Resolver responsibilities

Each resolver provides:

- `list_entities` / `get_entity`
- `get_anchor_date`, `get_recipient`, `get_reference`
- `is_eligible` (generation)
- `should_cancel_instance` (processing)
- `build_template_context`, `build_text_message`
- `get_whatsapp_template_spec`, default label/sender
