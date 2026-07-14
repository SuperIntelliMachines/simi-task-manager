/**
 * Supported outbound reminder channels for the Generic Reminder Engine.
 *
 * Canonical keys come from GET /api/v1/reminders/channels (ChannelService).
 * Labels are derived for display only — the channel *list* is not hardcoded.
 */

import { apiClient } from "../api/client";

export type ReminderChannelKey = string;

export type ReminderChannelOption = {
  key: ReminderChannelKey;
  label: string;
  /** Value sent to Generic Reminder APIs as `channel` / `channels[]`. */
  apiChannel: ReminderChannelKey;
};

export const DEFAULT_REMINDER_CHANNEL: ReminderChannelKey = "in_app";

/** Display-only labels for known keys; unknown keys are title-cased. */
function channelLabel(key: string): string {
  const normalized = key.trim().toLowerCase();
  if (normalized === "in_app") return "In App";
  if (normalized === "sms") return "SMS";
  if (normalized === "whatsapp") return "WhatsApp";
  return normalized
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toOptions(keys: string[]): ReminderChannelOption[] {
  return keys.map((key) => {
    const normalized = key.trim().toLowerCase();
    return { key: normalized, label: channelLabel(normalized), apiChannel: normalized };
  });
}

/** Soft fallback used until metadata API responds (same keys as ChannelService). */
export const REMINDER_CHANNEL_OPTIONS: ReminderChannelOption[] = toOptions([
  "in_app",
  "email",
  "sms",
  "whatsapp",
  "telegram",
]);

let cachedChannelOptions: ReminderChannelOption[] | null = null;

export async function loadReminderChannelOptions(): Promise<ReminderChannelOption[]> {
  if (cachedChannelOptions) return cachedChannelOptions;
  try {
    const keys = await apiClient.listReminderChannels();
    if (Array.isArray(keys) && keys.length > 0) {
      cachedChannelOptions = toOptions(keys);
      return cachedChannelOptions;
    }
  } catch {
    // Fall through to soft fallback matching ChannelService keys.
  }
  cachedChannelOptions = REMINDER_CHANNEL_OPTIONS;
  return cachedChannelOptions;
}

export function isReminderChannelKey(value: string | null | undefined): value is ReminderChannelKey {
  return Boolean(value && value.trim());
}

export function getReminderChannelOption(key: string | null | undefined): ReminderChannelOption {
  const normalized = (key || DEFAULT_REMINDER_CHANNEL).trim().toLowerCase();
  const pool = cachedChannelOptions ?? REMINDER_CHANNEL_OPTIONS;
  return (
    pool.find((option) => option.key === normalized) ?? {
      key: normalized,
      label: channelLabel(normalized),
      apiChannel: normalized,
    }
  );
}

export function parseReminderChannelKey(
  channels: string[] | string | null | undefined
): ReminderChannelKey {
  const first = Array.isArray(channels) ? channels[0] : channels;
  const normalized = (first || DEFAULT_REMINDER_CHANNEL).trim().toLowerCase();
  return isReminderChannelKey(normalized) ? normalized : DEFAULT_REMINDER_CHANNEL;
}

export function getReminderChannelLabel(key: string | null | undefined): string {
  return getReminderChannelOption(key).label;
}
