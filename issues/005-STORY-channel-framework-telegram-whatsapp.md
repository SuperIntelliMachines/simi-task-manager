---
title: "[ATM-005] [Story] Telegram and WhatsApp Channel Framework"
labels: [story, backend, channels, telegram, whatsapp, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-005 - Telegram and WhatsApp Channel Framework

## Objective

Build a unified communication layer where tenants can choose Telegram, WhatsApp, or both for staff/customer reminders and inbound task updates.

## Implementation Steps

1. Define channel adapter interface:
   - normalize inbound payload
   - send outbound message
   - verify webhook
   - resolve identity
   - map provider errors

2. Implement `ChannelService`:
   - select adapter by channel
   - create inbound message records
   - create outbound message records
   - update provider status
   - enforce consent and opt-out

3. Implement Telegram adapter:
   - `POST /api/v1/telegram/webhook`
   - bot token config through Secret Manager reference
   - direct chat and group message support
   - inline action buttons for complete, snooze, renewed, follow-up later
   - identity linking by Telegram user ID/chat ID

4. Implement WhatsApp adapter:
   - `POST /api/v1/whatsapp/webhook`
   - Meta webhook verification challenge
   - signature verification
   - outbound template-message support
   - inbound reply capture
   - STOP/opt-out handling

5. Implement channel settings APIs:
   - list connections
   - create/update connection
   - test message
   - set contact preferred channel

6. Add mock adapters for automated tests.

## Acceptance Criteria

- [ ] Tenant can configure Telegram and WhatsApp connections.
- [ ] Contact can choose preferred channel.
- [ ] Reminder processor can send through selected channel.
- [ ] Telegram webhook stores inbound message and triggers processing.
- [ ] WhatsApp webhook verifies challenge/signature and stores inbound message.
- [ ] Opt-out stops future external reminders.

## Test Cases

- Telegram webhook normalizes text message.
- Telegram inline button updates reminder/task status.
- WhatsApp verification challenge returns expected response.
- WhatsApp inbound "STOP" updates contact consent.
- Outbound send failure records provider error.
- Mock channel adapter can be used by reminder tests.

## Validation

```bash
cd backend
python -m pytest tests/unit/channels/test_channel_service.py -v
python -m pytest tests/unit/channels/test_telegram_adapter.py -v
python -m pytest tests/unit/channels/test_whatsapp_adapter.py -v
python -m pytest tests/integration/test_channel_webhooks.py -v
```

