/**
 * Frontend API service for General Reminder Definition CRUD.
 * Maps between UI models and /api/v1/general-reminders.
 */
import {
  apiClient,
  type GeneralReminderDefinitionDto,
  type GeneralReminderUpsertDto,
} from "../lib/api/client";
import type { ReminderChannelKey } from "../lib/reminders/channels";
import type {
  ManagedReminder,
  ReminderDraft,
  ReminderListFilters,
  ReminderOffsetDirection,
  ReminderOffsetUnit,
  ReminderRecipientTarget,
  ReminderTriggerKind,
} from "../lib/reminder-management/types";

export type GeneralReminderListResult = {
  items: ManagedReminder[];
  total: number;
  limit: number;
  offset: number;
};

function parseRecipients(value: unknown[]): ReminderRecipientTarget[] {
  return value.map((item) => {
    if (item && typeof item === "object" && "id" in item) {
      const row = item as { id: unknown; label?: unknown };
      const id = String(row.id);
      return { id, label: row.label != null ? String(row.label) : id };
    }
    const id = String(item);
    return { id, label: id };
  });
}

function isOffsetUnit(value: string): value is ReminderOffsetUnit {
  return ["minutes", "hours", "days", "weeks", "months"].includes(value);
}

function isDirection(value: string): value is ReminderOffsetDirection {
  return value === "before" || value === "after";
}

function isTriggerKind(value: string): value is ReminderTriggerKind {
  return value === "date" || value === "workflow";
}

export function mapDefinitionToManaged(row: GeneralReminderDefinitionDto): ManagedReminder {
  const triggerKind = isTriggerKind(row.trigger.type) ? row.trigger.type : "date";
  const offsetUnit = isOffsetUnit(row.schedule.offset_unit) ? row.schedule.offset_unit : "days";
  const offsetDirection = isDirection(row.schedule.direction) ? row.schedule.direction : "before";
  const recipients = parseRecipients(row.recipient?.value ?? []);
  const enabled = Boolean(row.is_active);

  return {
    id: row.id,
    name: row.reminder_name,
    description: row.description ?? "",
    module: row.module_key,
    triggerKind,
    triggerKey: row.trigger.key,
    triggerLabel: row.trigger.key,
    offsetValue: row.schedule.offset_value,
    offsetUnit,
    offsetDirection,
    recipients,
    channels: (row.channels ?? []) as ReminderChannelKey[],
    templateId: row.template_key ?? null,
    enabled,
    status: enabled ? "active" : "disabled",
    nextTriggerAt: null,
    createdBy: row.created_by != null ? String(row.created_by) : "—",
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function draftToUpsertDto(draft: ReminderDraft): GeneralReminderUpsertDto {
  const recipients = draft.recipients;
  return {
    module_key: draft.module.trim(),
    reminder_name: draft.name.trim(),
    description: draft.description.trim() || null,
    trigger: {
      type: draft.triggerKind,
      key: draft.triggerKey,
    },
    schedule: {
      offset_value: draft.offsetValue,
      offset_unit: draft.offsetUnit,
      direction: draft.offsetDirection,
    },
    recipient: {
      type: recipients.length === 1 ? recipients[0].id : "multi",
      value: recipients.map((item) => ({ id: item.id, label: item.label })),
    },
    channels: [...draft.channels],
    template_key: draft.templateId?.trim() || null,
    is_active: draft.enabled,
  };
}

function buildListParams(filters?: Partial<ReminderListFilters> & { limit?: number; offset?: number }) {
  const limit = filters?.limit ?? 50;
  const offset = filters?.offset ?? 0;
  const q = filters?.search?.trim() || undefined;
  const module_key =
    filters?.module && filters.module !== "all" ? filters.module : undefined;

  let is_active: boolean | undefined;
  if (filters?.status === "active") is_active = true;
  else if (filters?.status === "disabled") is_active = false;

  return { q, module_key, is_active, limit, offset };
}

export const generalReminderService = {
  async listReminders(
    filters?: Partial<ReminderListFilters> & { limit?: number; offset?: number }
  ): Promise<GeneralReminderListResult> {
    const params = buildListParams(filters);
    const response = await apiClient.listGeneralReminders(params);
    let items = response.items.map(mapDefinitionToManaged);

    // Channel is not a backend filter — apply client-side on the current page.
    if (filters?.channel && filters.channel !== "all") {
      items = items.filter((row) => row.channels.includes(filters.channel as ReminderChannelKey));
    }

    return {
      items,
      total: response.total,
      limit: response.limit,
      offset: response.offset,
    };
  },

  async getReminder(id: string): Promise<ManagedReminder> {
    const row = await apiClient.getGeneralReminder(id);
    return mapDefinitionToManaged(row);
  },

  async createReminder(draft: ReminderDraft): Promise<ManagedReminder> {
    const row = await apiClient.createGeneralReminder(draftToUpsertDto(draft));
    return mapDefinitionToManaged(row);
  },

  async updateReminder(id: string, draft: ReminderDraft): Promise<ManagedReminder> {
    const row = await apiClient.updateGeneralReminder(id, draftToUpsertDto(draft));
    return mapDefinitionToManaged(row);
  },

  async setReminderEnabled(id: string, enabled: boolean): Promise<ManagedReminder> {
    const row = await apiClient.updateGeneralReminder(id, { is_active: enabled });
    return mapDefinitionToManaged(row);
  },

  async deleteReminder(id: string): Promise<void> {
    await apiClient.deleteGeneralReminder(id);
  },
};
