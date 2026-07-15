/**
 * Personal Reminder API client — maps to /api/v1/personal-reminders.
 */
import { apiClient } from "../api/client";
import type {
  PersonalReminder,
  PersonalReminderDraft,
  PersonalReminderListFilters,
  PersonalReminderListResponse,
  PersonalReminderUpsert,
} from "./types";

export function emptyPersonalReminderDraft(
  defaults?: Partial<PersonalReminderDraft>
): PersonalReminderDraft {
  const now = new Date();
  const date = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;

  return {
    title: "",
    description: "",
    reminderDate: date,
    reminderTime: time,
    channels: ["in_app"],
    email: "",
    mobileNumber: "",
    whatsappNumber: "",
    telegramChatId: "",
    templateId: "",
    customMessage: "",
    isActive: true,
    ...defaults,
  };
}

export function reminderToDraft(reminder: PersonalReminder): PersonalReminderDraft {
  const scheduled = new Date(reminder.scheduled_at);
  const valid = !Number.isNaN(scheduled.getTime());
  const reminderDate = valid
    ? [
        scheduled.getFullYear(),
        String(scheduled.getMonth() + 1).padStart(2, "0"),
        String(scheduled.getDate()).padStart(2, "0"),
      ].join("-")
    : reminder.scheduled_at.slice(0, 10);
  const reminderTime = valid
    ? `${String(scheduled.getHours()).padStart(2, "0")}:${String(scheduled.getMinutes()).padStart(2, "0")}`
    : "09:00";

  return emptyPersonalReminderDraft({
    title: reminder.title,
    description: reminder.description ?? "",
    reminderDate,
    reminderTime,
    channels: [...(reminder.channels ?? [])],
    email: reminder.email ?? "",
    mobileNumber: reminder.mobile_number ?? "",
    whatsappNumber: reminder.whatsapp_number ?? "",
    telegramChatId: reminder.telegram_chat_id ?? "",
    templateId: reminder.template_id ?? "",
    customMessage: reminder.custom_message ?? "",
    isActive: Boolean(reminder.is_active),
  });
}

/** Combine local date + time into an ISO-like datetime for the API (no timezone). */
export function combineDateAndTime(date: string, time: string): string {
  const normalizedTime = time.length === 5 ? `${time}:00` : time;
  return `${date}T${normalizedTime}`;
}

export function draftToUpsert(draft: PersonalReminderDraft): PersonalReminderUpsert {
  const channels = draft.channels.map((c) => c.trim().toLowerCase()).filter(Boolean);
  const hasEmail = channels.includes("email");
  const hasSms = channels.includes("sms");
  const hasWhatsapp = channels.includes("whatsapp");
  const hasTelegram = channels.includes("telegram");
  const rawTemplateId = draft.templateId.trim();
  const templateId = isUuid(rawTemplateId) ? rawTemplateId : null;
  const customMessage = draft.customMessage.trim() || null;

  return {
    title: draft.title.trim(),
    description: draft.description.trim() || null,
    scheduled_at: combineDateAndTime(draft.reminderDate, draft.reminderTime),
    channels,
    email: hasEmail ? draft.email.trim() || null : null,
    mobile_number: hasSms ? draft.mobileNumber.trim() || null : null,
    whatsapp_number: hasWhatsapp ? draft.whatsappNumber.trim() || null : null,
    telegram_chat_id: hasTelegram ? draft.telegramChatId.trim() || null : null,
    template_id: templateId,
    custom_message: customMessage,
    status: "PENDING",
    is_active: draft.isActive,
  };
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value
  );
}

export function validatePersonalReminderDraft(draft: PersonalReminderDraft): string | null {
  if (!draft.title.trim()) return "Reminder name is required.";
  if (!draft.reminderDate) return "Reminder date is required.";
  if (!draft.reminderTime) return "Reminder time is required.";
  if (draft.channels.length === 0) return "Select at least one channel.";

  const channels = new Set(draft.channels.map((c) => c.toLowerCase()));
  if (channels.has("email") && !draft.email.trim()) {
    return "Email address is required when Email is selected.";
  }
  if (channels.has("sms") && !draft.mobileNumber.trim()) {
    return "Mobile number is required when SMS is selected.";
  }
  if (channels.has("whatsapp") && !draft.whatsappNumber.trim()) {
    return "WhatsApp number is required when WhatsApp is selected.";
  }
  if (channels.has("telegram") && !draft.telegramChatId.trim()) {
    return "Telegram chat ID is required when Telegram is selected.";
  }
  return null;
}

function buildListParams(filters?: Partial<PersonalReminderListFilters> & { limit?: number; offset?: number }) {
  const limit = filters?.limit ?? filters?.pageSize ?? 50;
  const offset =
    filters?.offset ??
    (filters?.page != null && filters?.pageSize != null ? filters.page * filters.pageSize : 0);
  const q = filters?.search?.trim() || undefined;
  const status = filters?.status && filters.status !== "all" ? filters.status : undefined;

  let is_active: boolean | undefined;
  if (filters?.isActive === true) is_active = true;
  else if (filters?.isActive === false) is_active = false;

  return { q, status, is_active, limit, offset };
}

export const personalReminderApi = {
  async list(
    filters?: Partial<PersonalReminderListFilters> & { limit?: number; offset?: number }
  ): Promise<PersonalReminderListResponse> {
    const params = buildListParams(filters);
    const response = await apiClient.listPersonalReminders(params);
    let items = response.items;

    // Channel is not a backend filter — apply on the current page.
    if (filters?.channel && filters.channel !== "all") {
      const key = filters.channel.toLowerCase();
      items = items.filter((row) => row.channels.map((c) => c.toLowerCase()).includes(key));
    }

    return {
      items,
      total: response.total,
      limit: response.limit,
      offset: response.offset,
    };
  },

  async get(id: string): Promise<PersonalReminder> {
    return apiClient.getPersonalReminder(id);
  },

  async create(draft: PersonalReminderDraft): Promise<PersonalReminder> {
    return apiClient.createPersonalReminder(draftToUpsert(draft));
  },

  async update(id: string, draft: PersonalReminderDraft): Promise<PersonalReminder> {
    return apiClient.updatePersonalReminder(id, draftToUpsert(draft));
  },

  async setActive(id: string, isActive: boolean): Promise<PersonalReminder> {
    return apiClient.updatePersonalReminder(id, { is_active: isActive });
  },

  async remove(id: string): Promise<void> {
    await apiClient.deletePersonalReminder(id);
  },
};
