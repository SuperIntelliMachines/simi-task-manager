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
  ReminderRecurrenceUnit,
  ReminderStopCondition,
  ReminderTriggerKind,
} from "../lib/reminder-management/types";

export type GeneralReminderListResult = {
  items: ManagedReminder[];
  total: number;
  limit: number;
  offset: number;
};

function isOffsetUnit(value: string): value is ReminderOffsetUnit {
  return ["minutes", "hours", "days", "weeks", "months"].includes(value);
}

function isDirection(value: string): value is ReminderOffsetDirection {
  return value === "before" || value === "after";
}

function isTriggerKind(value: string): value is ReminderTriggerKind {
  return value === "date" || value === "workflow";
}

function isRecurrenceUnit(value: string): value is ReminderRecurrenceUnit {
  return ["hours", "days", "weeks", "months"].includes(value);
}

function isStopCondition(value: string): value is ReminderStopCondition {
  return [
    "entity_ineligible",
    "workflow_status_changed",
    "end_date_reached",
    "max_attempts_reached",
    "never",
  ].includes(value);
}

export function mapDefinitionToManaged(row: GeneralReminderDefinitionDto): ManagedReminder {
  const triggerKind = isTriggerKind(row.trigger.type) ? row.trigger.type : "date";
  const offsetUnit = isOffsetUnit(row.schedule.offset_unit) ? row.schedule.offset_unit : "days";
  const offsetDirection = isDirection(row.schedule.direction) ? row.schedule.direction : "before";
  const enabled = Boolean(row.is_active);
  const recurrence = row.recurrence ?? {
    repeat_enabled: false,
    repeat_frequency_value: null,
    repeat_frequency_unit: null,
    max_attempts: null,
    stop_condition: "entity_ineligible",
    stop_condition_config: null,
  };
  const repeatUnit = recurrence.repeat_frequency_unit;
  const repeatFrequencyUnit = repeatUnit && isRecurrenceUnit(repeatUnit) ? repeatUnit : "hours";
  const stopCondition =
    recurrence.stop_condition && isStopCondition(recurrence.stop_condition)
      ? recurrence.stop_condition
      : "entity_ineligible";

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
    repeatEnabled: Boolean(recurrence.repeat_enabled),
    repeatFrequencyValue: recurrence.repeat_frequency_value ?? 24,
    repeatFrequencyUnit,
    maxAttempts: recurrence.max_attempts ?? null,
    stopCondition,
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
    recurrence: {
      repeat_enabled: draft.repeatEnabled,
      repeat_frequency_value: draft.repeatEnabled ? draft.repeatFrequencyValue : null,
      repeat_frequency_unit: draft.repeatEnabled ? draft.repeatFrequencyUnit : null,
      max_attempts: draft.maxAttempts,
      stop_condition: draft.stopCondition,
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
