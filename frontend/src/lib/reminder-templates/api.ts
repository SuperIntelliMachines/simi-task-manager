import { apiClient } from "../api/client";
import type {
  ReminderTemplateDefinitionListResponse,
  ReminderTemplateDraft,
  ReminderTemplateListFilters,
  ReminderTemplateListResponse,
  ReminderTemplateRecord,
  ReminderTemplateUpsert,
} from "./types";

export const REMINDER_TEMPLATE_CHANNEL_OPTIONS = [
  { value: "email", label: "Email" },
  { value: "in_app", label: "In App" },
  { value: "sms", label: "SMS" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
] as const;

export function emptyReminderTemplateDraft(
  defaults?: Partial<ReminderTemplateDraft>
): ReminderTemplateDraft {
  return {
    name: "",
    channel: "email",
    subject: "",
    title: "",
    body: "",
    variablesText: "",
    isActive: true,
    whatsappTemplateName: "",
    ...defaults,
  };
}

export function recordToDraft(record: ReminderTemplateRecord): ReminderTemplateDraft {
  return emptyReminderTemplateDraft({
    name: record.name,
    channel: record.channel,
    subject: record.subject ?? "",
    title: record.title ?? "",
    body: record.body,
    variablesText: (record.variables ?? []).join(", "),
    isActive: record.is_active,
    whatsappTemplateName: record.whatsapp_template_name ?? record.name,
  });
}

export function parseVariables(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function draftToUpsert(draft: ReminderTemplateDraft): ReminderTemplateUpsert {
  const channel = draft.channel.trim().toLowerCase();
  const variables = parseVariables(draft.variablesText);
  const payload: ReminderTemplateUpsert = {
    name: draft.name.trim(),
    channel,
    body: draft.body.trim(),
    variables,
    is_active: draft.isActive,
  };

  if (channel === "email") {
    payload.subject = draft.subject.trim() || null;
  }
  if (channel === "in_app") {
    payload.title = draft.title.trim() || null;
  }
  if (channel === "whatsapp") {
    payload.whatsapp_template_name = draft.whatsappTemplateName.trim() || draft.name.trim();
  }

  return payload;
}

export function validateReminderTemplateDraft(draft: ReminderTemplateDraft): string | null {
  if (!draft.name.trim()) return "Template name is required.";
  if (!draft.channel) return "Channel is required.";
  if (!draft.body.trim()) return "Template body is required.";

  const channel = draft.channel.toLowerCase();
  if (channel === "email" && !draft.subject.trim()) {
    return "Subject is required for email templates.";
  }
  if (channel === "in_app" && !draft.title.trim()) {
    return "Title is required for in-app templates.";
  }
  if (channel === "whatsapp" && !draft.whatsappTemplateName.trim() && !draft.name.trim()) {
    return "WhatsApp template name is required.";
  }
  return null;
}

export function formatApprovalStatus(status: string | null | undefined): string {
  if (!status) return "—";
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildListParams(filters?: Partial<ReminderTemplateListFilters> & { limit?: number; offset?: number }) {
  const q = filters?.search?.trim() || undefined;
  const channel =
    filters?.channel && filters.channel !== "all" ? String(filters.channel) : undefined;
  let is_active: boolean | undefined;
  if (filters?.isActive === true) is_active = true;
  else if (filters?.isActive === false) is_active = false;
  return {
    q,
    channel,
    is_active,
    limit: filters?.limit ?? 100,
    offset: filters?.offset ?? 0,
  };
}

export const reminderTemplateApi = {
  async list(
    filters?: Partial<ReminderTemplateListFilters> & { limit?: number; offset?: number }
  ): Promise<ReminderTemplateListResponse> {
    return apiClient.listReminderTemplates(buildListParams(filters));
  },

  async listDefinitions(params?: {
    isActive?: boolean;
  }): Promise<ReminderTemplateDefinitionListResponse> {
    return apiClient.listReminderTemplateDefinitions({
      is_active: params?.isActive,
    });
  },

  async get(id: string): Promise<ReminderTemplateRecord> {
    return apiClient.getReminderTemplate(id);
  },

  async create(draft: ReminderTemplateDraft): Promise<ReminderTemplateRecord> {
    return apiClient.createReminderTemplate(draftToUpsert(draft));
  },

  async update(id: string, draft: ReminderTemplateDraft): Promise<ReminderTemplateRecord> {
    return apiClient.updateReminderTemplate(id, draftToUpsert(draft));
  },

  async remove(id: string): Promise<void> {
    await apiClient.deleteReminderTemplate(id);
  },
};
