export type TaskStatus = "open" | "snoozed" | "completed" | "canceled";
export type TaskDomain = "general" | "insurance" | "construction" | "medical_office";
export type UserRole = "owner" | "manager" | "staff" | "viewer";

export type TaskRecord = {
  id: number;
  organization_id: number;
  title: string;
  description: string | null;
  domain: TaskDomain;
  status: TaskStatus;
  due_at: string | null;
  priority: "low" | "medium" | "high";
  assignee: string | null;
  audit: Array<{ id: string; label: string; at: string; detail?: string }>;
};

export type TaskFilters = {
  organizationId: number;
  status: string;
  domain: string;
  assignee: string;
  dueDate: string;
  priority: string;
};

export type TaskCreateInput = {
  organization_id: number;
  title: string;
  description?: string;
  due_at?: string | null;
  domain: TaskDomain;
  actor_user_id?: number | null;
  priority?: "low" | "medium" | "high";
};

export type TaskPatchInput = {
  title?: string;
  description?: string;
  due_at?: string | null;
  domain?: TaskDomain;
  status?: TaskStatus;
  actor_user_id?: number | null;
  priority?: "low" | "medium" | "high";
};

export type ApprovalRequestRecord = {
  id: number;
  organization_id: number;
  status: string;
  reason: string | null;
  proposed_action: {
    action_type: string;
    payload: Record<string, unknown>;
  };
  created_at: string;
};

export type ChannelConnectionRecord = {
  id: number;
  organization_id: number;
  channel: "telegram" | "whatsapp";
  status: string;
  provider_reference: string | null;
  settings: Record<string, unknown>;
};

export type ChannelConnectionInput = {
  organization_id: number;
  channel: "telegram" | "whatsapp";
  provider_reference: string;
  status?: string;
  settings: Record<string, unknown>;
};

export type TestMessageInput = {
  recipient: string;
  text: string;
};

export type NotificationPreferenceRecord = {
  id: number;
  organization_id: number;
  contact_id: number | null;
  user_id: number | null;
  purpose: string;
  preferred_channel: string;
  fallback_channel: string | null;
  opt_out: boolean;
};

export type InAppNotificationRecord = {
  id: number;
  organization_id: number;
  user_id: number;
  entity_type: string;
  entity_id: number;
  reminder_instance_id: number | null;
  title: string;
  message: string;
  priority: string;
  status: "UNREAD" | "READ" | string;
  metadata: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
  created_by: number | null;
};

export type InAppNotificationListResponse = {
  notifications: InAppNotificationRecord[];
};

export type UnreadCountResponse = {
  unread_count: number;
};

export type PolicyCustomReminder = {
  id?: number;
  reminder_unit: string;
  reminder_value: number;
  dnd_start_time?: string | null;
  dnd_end_time?: string | null;
};

export type InsurancePolicyCard = {
  id: number;
  policy_number: string;
  policyholder_name: string;
  policy_type: string | null;
  carrier?: string | null;
  renewal_frequency?: string | null;
  premium?: number | string | null;
  expiry_date: string;
  grace_period_days?: number;
  preferred_channel: string[] | null;
  reminder_type?: string | null;
  reminder_unit?: string | null;
  reminder_value?: number | null;
  custom_reminders?: PolicyCustomReminder[];
  dnd_start_time?: string | null;
  dnd_end_time?: string | null;
  status: string;
  document_name?: string | null;
  document_path?: string | null;
  mobile_number?: string | null;
  mobile?: string | null;
  contact_phone?: string | null;
  email?: string | null;
  contact_email?: string | null;
  assigned_agent_user_id?: number | string | null;
  created_at?: string;
  updated_at?: string;
};

export type PolicyRenewalSmsResponse = {
  mode: "sent" | "client" | string;
  mobile: string;
  policyholder_name: string;
  policy_number: string;
  payment_link: string;
  logged_in_user_name: string;
  message: string;
  sms_uri?: string | null;
};

export type PolicyDocumentUploadResponse = {
  document_name: string;
  document_path: string;
};

export type PolicyReminderItem = {
  id: number;
  policy_id: number;
  reminder_type?: string | null;
  reminder_at: string;
  stage: number;
  stage_direction?: string | null;
  stage_unit?: string | null;
  stage_value?: number | null;
  status: string;
  channel: string;
  sent_at?: string | null;
};

export type PolicyRenewResponse = {
  policy: InsurancePolicyCard;
  reminders: PolicyReminderItem[];
};

export type InsuranceLeadCard = {
  id: number;
  contact_name?: string;
  customerName?: string;
  contact_phone?: string | null;
  contact_email?: string | null;
  email?: string | null;
  policyType?: string | null;
  status: string;
  followup_due_at: string | null;
};

export type InsuranceDashboard = {
  due_renewals: InsurancePolicyCard[];
  expiring_policies: InsurancePolicyCard[];
  grace_period_policies: InsurancePolicyCard[];
  lapsed_policies: InsurancePolicyCard[];
  pending_followups: InsuranceLeadCard[];
  policy_summary?: {
    total_policies: number;
    active_policies: number;
    grace_period_policies: number;
    lapsed_policies: number;
    expiring_soon_policies: number;
  };
  lead_followup_overview?: {
    total_leads: number;
    upcoming_followups: number;
    due_in_48_hours: number;
    missed_followups: number;
  };
  renewal_intelligence?: {
    points: Array<{
      policy_id: number;
      customer_name: string;
      policy_number: string;
      product_type: string | null;
      renewal_frequency: string | null;
      expiry_date: string;
      premium: number;
      renewal_status: string;
      renewal_status_label: string;
      days_until_due: number | null;
      days_overdue: number | null;
      assigned_agent_user_id: number | string | null;
      assigned_agent_name: string | null;
      reminders_sent_count?: number;
    }>;
    filters: {
      agents: Array<{ value: string; label: string }>;
      product_types: string[];
    };
  };
  counts: {
    total_policies?: number;
    active_policies?: number;
    expiring_policies?: number;
    due_renewals: number;
    grace_period_policies: number;
    lapsed_policies: number;
    pending_followups: number;
    due_followups?: number;
    overdue_followups?: number;
  };
  conversion_metrics: {
    demo_to_policy_rate: number;
    renewal_rate: number;
  };
};

export type ConstructionDashboard = {
  overdueTasks: number;
  blockedTasks: number;
  workerLoad: Array<{ name: string; openTasks: number }>;
  siteProgress: Array<{ site: string; completion: number }>;
};

export type MedicalDashboard = {
  tomorrowPrep: Array<{ id: string; patient: string; summary: string }>;
  overdueInternalTasks: number;
  queues: Array<{ id: string; patient: string; lane: string; owner: string }>;
};

export type CommandPreview = {
  status: "preview" | "needs_approval" | "needs_clarification" | "executed";
  domain: string;
  confidence: number;
  extractedFields: string[];
  missingFields: string[];
  approvalReason?: string;
  resultMessage?: string;
};

export type CustomerRecord = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
};

export type OwnerUserRecord = { id: number; email: string };

export type HealthUsageRecord = { health_score: number; active_users: number; agent_invocations: number };

export type UsageRecord = { monthly_requests: number; storage_used: string };

export type AuditLogRecord = { id: number; organization_id: number; event_type: string; entity_type: string; entity_id: string; payload: Record<string, unknown>; created_at: string };

export type ReminderAttemptRecord = { id: number; organization_id: number; reminder_id: number; attempt_number: number; status: string; error_message?: string; next_retry_at?: string; created_at: string };

export type AgentInvocationRecord = { id: number; organization_id: number; actor_user_id?: number; agent: string; domain: string; intent: string; confidence: number; input_summary: string; output_summary: string; created_at: string };

export type SupportAccessRecord = { id: number; organization_id: number; created_by_user_id?: number; started_at?: string; ended_at?: string; created_at: string };

export type ReminderConfigRecord = {
  id: number;
  organization_id: number;
  entity_type: string;
  entity_id: number;
  channel: string;
  template_key?: string | null;
  entity_label?: string | null;
  sender_name?: string | null;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
  offset_value: number;
  offset_unit: string;
  time_of_day?: string | null;
  scheduled_at?: string | null;
  dnd_start?: string | null;
  dnd_end?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type ReminderConfigGroupRecord = {
  config_id: number;
  organization_id: number;
  entity_type: string;
  entity_id: number;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
  offset_value: number;
  offset_unit: string;
  trigger_offset_value?: number;
  trigger_offset_unit?: string;
  trigger_offset_direction?: string;
  repeat_enabled?: boolean;
  repeat_frequency_value?: number | null;
  repeat_frequency_unit?: string | null;
  max_attempts?: number | null;
  stop_condition?: string;
  stop_condition_config?: Record<string, unknown> | null;
  time_of_day?: string | null;
  channels: string[];
  is_active: boolean;
};

export type ReminderConfigListResponse = {
  configs: ReminderConfigRecord[];
};

export type ReminderConfigGroupListResponse = {
  configs: ReminderConfigGroupRecord[];
};

export type ReminderDefinitionInput = {
  channels: string[];
  offset_value?: number | null;
  offset_unit?: string;
  time_of_day?: string | null;
  scheduled_at?: string | null;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
  trigger_offset_value?: number | null;
  trigger_offset_unit?: string;
  trigger_offset_direction?: string;
  repeat_enabled?: boolean;
  repeat_frequency_value?: number | null;
  repeat_frequency_unit?: string | null;
  max_attempts?: number | null;
  stop_condition?: string;
  stop_condition_config?: Record<string, unknown> | null;
};

export type ReminderSettingsSaveInput = {
  organization_id: number;
  entity_type: string;
  entity_id: number;
  channels?: string[];
  offsets?: Array<{
    offset_value: number;
    offset_unit: string;
    time_of_day?: string | null;
    anchor_type?: string;
    anchor_key?: string;
    offset_direction?: string;
  }>;
  reminders?: ReminderDefinitionInput[] | null;
  template_key?: string;
  entity_label?: string | null;
  sender_name?: string | null;
  dnd_start?: string | null;
  dnd_end?: string | null;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
};

export type ReminderConfigCreateInput = {
  organization_id: number;
  entity_type: string;
  entity_id: number;
  reminders?: ReminderDefinitionInput[] | null;
  channel?: string | null;
  offsets?: number[] | null;
  offset_unit?: string;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
  template_key?: string | null;
  entity_label?: string | null;
  sender_name?: string | null;
  dnd_start?: string | null;
  dnd_end?: string | null;
  /** When false, append configs without deactivating siblings (Create Reminder Relative). */
  replace_existing?: boolean;
};

export type ReminderConfigUpdateInput = {
  offset_value?: number | null;
  offset_unit?: string | null;
  channel?: string | null;
  channels?: string[] | null;
  time_of_day?: string | null;
  scheduled_at?: string | null;
  anchor_type?: string | null;
  anchor_key?: string | null;
  offset_direction?: string | null;
  dnd_start?: string | null;
  dnd_end?: string | null;
  is_active?: boolean | null;
  repeat_enabled?: boolean | null;
  repeat_frequency_value?: number | null;
  repeat_frequency_unit?: string | null;
  max_attempts?: number | null;
  stop_condition?: string | null;
  stop_condition_config?: Record<string, unknown> | null;
};
