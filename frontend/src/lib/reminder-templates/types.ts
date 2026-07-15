/** Types for Reminder Template CRUD. */

export type ReminderTemplateChannel = "email" | "in_app" | "sms" | "telegram" | "whatsapp";

export type WhatsAppApprovalStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected";

export type ReminderTemplateRecord = {
  id: string;
  organization_id: number;
  created_by: number | null;
  name: string;
  channel: ReminderTemplateChannel | string;
  subject: string | null;
  title: string | null;
  body: string;
  variables: string[];
  is_active: boolean;
  whatsapp_template_name: string | null;
  approval_status: WhatsAppApprovalStatus | string | null;
  meta_template_id: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type ReminderTemplateDraft = {
  name: string;
  channel: ReminderTemplateChannel | string;
  subject: string;
  title: string;
  body: string;
  variablesText: string;
  isActive: boolean;
  whatsappTemplateName: string;
};

export type ReminderTemplateListFilters = {
  search: string;
  channel: ReminderTemplateChannel | "all" | string;
  isActive: boolean | "all";
};

export type ReminderTemplateUpsert = {
  name: string;
  channel: string;
  subject?: string | null;
  title?: string | null;
  body: string;
  variables: string[];
  is_active: boolean;
  whatsapp_template_name?: string | null;
};

export type ReminderTemplateListResponse = {
  items: ReminderTemplateRecord[];
  total: number;
  limit: number;
  offset: number;
};
