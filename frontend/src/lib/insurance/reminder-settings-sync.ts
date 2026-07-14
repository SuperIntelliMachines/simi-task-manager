import { apiClient } from "../api/client";
import type { ReminderConfigGroupRecord, ReminderConfigRecord } from "../api/types";
import {
  DEFAULT_RENEWAL_REMINDER_CYCLE_DAYS,
  sanitizeReminderUnit,
  type CustomReminderItem,
  type ReminderType,
} from "./custom-reminder-config";

export const POLICY_REMINDER_ENTITY_TYPE = "policy";
export const POLICY_REMINDER_TEMPLATE_KEY = "policy_renewal_reminder";

function formatTimeForInput(value: string): string {
  return value.length >= 5 ? value.slice(0, 5) : value;
}

type ReminderOffsetSource = Pick<
  ReminderConfigRecord,
  "offset_value" | "offset_unit" | "is_active" | "dnd_start" | "dnd_end"
> | Pick<
  ReminderConfigGroupRecord,
  "offset_value" | "offset_unit" | "is_active"
> & { dnd_start?: string | null; dnd_end?: string | null };

export function customRemindersFromReminderConfigs(configs: ReminderOffsetSource[]): CustomReminderItem[] {
  const seen = new Set<string>();
  const items: CustomReminderItem[] = [];

  for (const config of configs) {
    if (!config.is_active) {
      continue;
    }
    const key = `${config.offset_unit}:${config.offset_value}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    items.push({
      reminder_unit: sanitizeReminderUnit(config.offset_unit),
      reminder_value: config.offset_value,
    });
  }

  return items.sort((left, right) => {
    if (left.reminder_unit === right.reminder_unit) {
      return right.reminder_value - left.reminder_value;
    }
    return left.reminder_unit.localeCompare(right.reminder_unit);
  });
}

export function dndFromReminderConfigs(configs: ReminderOffsetSource[]): {
  start: string | null;
  end: string | null;
} {
  const first = configs.find((config) => config.is_active && (config.dnd_start || config.dnd_end));
  if (!first) {
    return { start: null, end: null };
  }

  return {
    start: first.dnd_start ? formatTimeForInput(first.dnd_start) : null,
    end: first.dnd_end ? formatTimeForInput(first.dnd_end) : null,
  };
}

export function buildReminderOffsets(
  reminderType: ReminderType,
  customReminders: CustomReminderItem[]
): Array<{ offset_value: number; offset_unit: string }> {
  if (reminderType === "default") {
    return DEFAULT_RENEWAL_REMINDER_CYCLE_DAYS.map((days) => ({
      offset_value: days,
      offset_unit: "days",
    }));
  }

  return customReminders.map((item) => ({
    offset_value: item.reminder_value,
    offset_unit: item.reminder_unit,
  }));
}

export function buildPolicyEntityLabel(policyType: string | null | undefined): string {
  const label = (policyType || "Policy").trim();
  return `${label} Renewal`;
}

export async function savePolicyReminderSettings(input: {
  organizationId: number;
  policyId: number;
  reminderType: ReminderType;
  preferredChannels: string[];
  customReminders: CustomReminderItem[];
  policyType?: string | null;
  dndStart?: string | null;
  dndEnd?: string | null;
}) {
  const offsets = buildReminderOffsets(input.reminderType, input.customReminders);
  if (offsets.length === 0) {
    return;
  }

  return apiClient.saveReminderSettings({
    organization_id: input.organizationId,
    entity_type: POLICY_REMINDER_ENTITY_TYPE,
    entity_id: input.policyId,
    channels: input.preferredChannels,
    offsets,
    template_key: POLICY_REMINDER_TEMPLATE_KEY,
    entity_label: buildPolicyEntityLabel(input.policyType),
    dnd_start: input.reminderType === "personalized" ? input.dndStart ?? null : null,
    dnd_end: input.reminderType === "personalized" ? input.dndEnd ?? null : null,
  });
}
