import { ApiRequestError, parseApiErrorResponse } from "./errors";
import { mockApi } from "./mock-store";
import type {
  ApprovalRequestRecord,
  ChannelConnectionInput,
  ChannelConnectionRecord,
  CommandPreview,
  ConstructionDashboard,
  InsuranceDashboard,
  MedicalDashboard,
  NotificationPreferenceRecord,
  TaskCreateInput,
  TaskFilters,
  TaskPatchInput,
  TaskRecord,
  CustomerRecord,
  OwnerUserRecord,
  HealthUsageRecord,
  UsageRecord,
  AuditLogRecord,
  ReminderAttemptRecord,
  AgentInvocationRecord,
  SupportAccessRecord,
  InsurancePolicyCard,
  PolicyDocumentUploadResponse,
  PolicyRenewalSmsResponse,
  ReminderConfigCreateInput,
  ReminderConfigGroupListResponse,
  ReminderConfigGroupRecord,
  ReminderConfigListResponse,
  ReminderConfigUpdateInput,
  ReminderSettingsSaveInput,
  InAppNotificationListResponse,
  InAppNotificationRecord,
  UnreadCountResponse,
} from "./types";

/** Platform general reminder definition DTO (CRUD API). */
export type GeneralReminderUpsertDto = {
  module_key: string;
  reminder_name: string;
  description?: string | null;
  trigger: { type: string; key: string };
  schedule: { offset_value: number; offset_unit: string; direction: string };
  recipient: { type: string; value: unknown[] };
  channels: string[];
  template_key?: string | null;
  is_active: boolean;
};

export type GeneralReminderDefinitionDto = GeneralReminderUpsertDto & {
  id: string;
  organization_id: number;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

const API_BASE = "/api/v1";

function buildUrl(path: string, params?: Record<string, string | number | boolean | null | undefined>) {
  const url = new URL(`${window.location.origin}${API_BASE}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === "" || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

function authHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem("atm:token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch {
    // ignore storage errors
  }
  return {};
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw parseApiErrorResponse(response.status, body);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export function buildTaskListUrl(filters: TaskFilters) {
  return buildUrl("/tasks", {
    organization_id: filters.organizationId,
    status: filters.status || undefined,
    domain: filters.domain || undefined,
    assignee: filters.assignee || undefined,
    due_date: filters.dueDate || undefined,
    priority: filters.priority || undefined,
  });
}

export const apiClient = {
  async listTasks(filters: TaskFilters): Promise<TaskRecord[]> {
    if (filters.organizationId == null || filters.organizationId <= 0) {
      return [];
    }
    try {
      return await requestJson<TaskRecord[]>("/tasks", undefined, {
        organization_id: filters.organizationId,
        status: filters.status || undefined,
        domain: filters.domain || undefined,
        assignee: filters.assignee || undefined,
        due_date: filters.dueDate || undefined,
        priority: filters.priority || undefined,
      });
    } catch {
      return mockApi.listTasks(filters);
    }
  },
  async createTask(input: TaskCreateInput): Promise<TaskRecord> {
    try {
      return await requestJson<TaskRecord>("/tasks", { method: "POST", body: JSON.stringify(input) });
    } catch {
      return mockApi.createTask(input);
    }
  },
  async patchTask(taskId: number, input: TaskPatchInput): Promise<TaskRecord> {
    try {
      return await requestJson<TaskRecord>(`/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(input) });
    } catch {
      return mockApi.patchTask(taskId, input);
    }
  },
  async completeTask(taskId: number, actorUserId?: number | null): Promise<TaskRecord> {
    try {
      return await requestJson<TaskRecord>(`/tasks/${taskId}/complete`, {
        method: "POST",
        body: JSON.stringify({ actor_user_id: actorUserId ?? null, cancel_future_reminders: true }),
      });
    } catch {
      return mockApi.completeTask(taskId);
    }
  },
  async snoozeTask(taskId: number, dueAt: string, actorUserId?: number | null): Promise<TaskRecord> {
    try {
      return await requestJson<TaskRecord>(`/tasks/${taskId}/snooze`, {
        method: "POST",
        body: JSON.stringify({ due_at: dueAt, actor_user_id: actorUserId ?? null }),
      });
    } catch {
      return mockApi.snoozeTask(taskId, dueAt);
    }
  },
  async listApprovalRequests(organizationId: number): Promise<ApprovalRequestRecord[]> {
    try {
      return await requestJson<ApprovalRequestRecord[]>("/approval-requests", undefined, { organization_id: organizationId });
    } catch {
      return mockApi.listApprovals();
    }
  },
  async listChannelConnections(organizationId: number): Promise<ChannelConnectionRecord[]> {
    try {
      return await requestJson<ChannelConnectionRecord[]>("/channel-connections", undefined, { organization_id: organizationId });
    } catch {
      return mockApi.listConnections();
    }
  },
  async upsertChannelConnection(input: ChannelConnectionInput): Promise<ChannelConnectionRecord> {
    try {
      return await requestJson<ChannelConnectionRecord>("/channel-connections", { method: "POST", body: JSON.stringify(input) });
    } catch {
      return mockApi.upsertConnection(input);
    }
  },
  async sendChannelTestMessage(connectionId: number, recipient: string, text: string) {
    try {
      return await requestJson(`/channel-connections/${connectionId}/test`, {
        method: "POST",
        body: JSON.stringify({ recipient, text }),
      });
    } catch {
      return mockApi.sendTestMessage(connectionId, { recipient, text });
    }
  },
  async listNotificationPreferences(organizationId: number): Promise<NotificationPreferenceRecord[]> {
    try {
      return await requestJson<NotificationPreferenceRecord[]>("/notification-preferences", undefined, { organization_id: organizationId });
    } catch {
      return mockApi.listPreferences();
    }
  },
  // Admin / Customer APIs
  async listCustomers(): Promise<CustomerRecord[]> {
    return await requestJson<CustomerRecord[]>("/admin/customers");
  },
  async createCustomer(input: { name: string }): Promise<CustomerRecord> {
    return await requestJson<CustomerRecord>("/admin/customers", { method: "POST", body: JSON.stringify(input) });
  },
  async getCustomer(id: number): Promise<CustomerRecord> {
    return await requestJson<CustomerRecord>(`/admin/customers/${id}`);
  },
  async updateCustomer(id: number, updates: Partial<CustomerRecord>): Promise<CustomerRecord> {
    return await requestJson<CustomerRecord>(`/admin/customers/${id}`, { method: "PATCH", body: JSON.stringify(updates) });
  },
  async onboardCustomer(id: number): Promise<{ owner_user: OwnerUserRecord; agents_enabled: boolean; workflows_configured: boolean; message_templates_configured: boolean; sample_workflow_run: boolean }>
  {
    return await requestJson(`/admin/customers/${id}/onboard`, { method: "POST" });
  },
  async getCustomerHealth(id: number): Promise<HealthUsageRecord> {
    return await requestJson<HealthUsageRecord>(`/admin/customers/${id}/health`);
  },
  async getCustomerUsage(id: number): Promise<UsageRecord> {
    return await requestJson<UsageRecord>(`/admin/customers/${id}/usage`);
  },
  async getCustomerAudit(id: number): Promise<{ audit_logs: AuditLogRecord[] }> {
    return await requestJson<{ audit_logs: AuditLogRecord[] }>(`/admin/customers/${id}/audit`);
  },
  async getFailedReminders(id: number): Promise<{ failed_reminders: ReminderAttemptRecord[] }> {
    return await requestJson<{ failed_reminders: ReminderAttemptRecord[] }>(`/admin/customers/${id}/failed-reminders`);
  },
  async getAgentInvocations(id: number): Promise<{ invocations: AgentInvocationRecord[] }> {
    return await requestJson<{ invocations: AgentInvocationRecord[] }>(`/admin/customers/${id}/agent-invocations`);
  },
  async getSupportAccess(id: number): Promise<{ access_sessions: SupportAccessRecord[] }> {
    return await requestJson<{ access_sessions: SupportAccessRecord[] }>(`/admin/customers/${id}/support-access`);
  },
  async updateNotificationPreference(preferenceId: number, updates: Partial<NotificationPreferenceRecord>) {
    try {
      return await requestJson<NotificationPreferenceRecord>(`/notification-preferences/${preferenceId}`, {
        method: "PUT",
        body: JSON.stringify(updates),
      });
    } catch {
      return mockApi.updatePreference(preferenceId, updates);
    }
  },
  async insuranceDashboard(organizationId: number): Promise<InsuranceDashboard> {
    const data = await requestJson<InsuranceDashboard>("/insurance/dashboard", undefined, { organization_id: organizationId });
    return {
      ...data,
      conversion_metrics: data.conversion_metrics ?? { demo_to_policy_rate: 62, renewal_rate: 84 },
    };
  },
  // Insurance CRUD + workflows
  async listPolicies(organizationId: number, status?: string): Promise<InsurancePolicyCard[]> {
    return await requestJson<InsurancePolicyCard[]>("/insurance/policies", undefined, {
      organization_id: organizationId,
      status,
    });
  },
  async getPolicy(policyId: number) {
    try {
      return await requestJson<InsurancePolicyCard>(`/insurance/policies/${policyId}`);
    } catch (error) {
      if (error instanceof ApiRequestError) {
        throw error;
      }
      return mockApi.getPolicy(policyId);
    }
  },
  async createPolicy(input: any) {
    return await requestJson<any>('/insurance/policies', { method: 'POST', body: JSON.stringify(input) });
  },
  async uploadPolicyDocument(file: File, policyId?: number | null): Promise<PolicyDocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (policyId != null) {
      formData.append("policy_id", String(policyId));
    }

    const response = await fetch(buildUrl("/insurance/policies/upload-document"), {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = "Upload failed. Please try again.";
      try {
        const data = (await response.json()) as { detail?: string | { msg?: string }[] };
        if (typeof data.detail === "string") {
          message = data.detail;
        } else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
          message = data.detail[0].msg;
        }
      } catch {
        // keep default message
      }
      throw new Error(message);
    }

    return (await response.json()) as PolicyDocumentUploadResponse;
  },
  async updatePolicy(policyId: number, updates: any, actorUserId?: number | null) {
    try {
      return await requestJson<any>(`/insurance/policies/${policyId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      }, { actor_user_id: actorUserId ?? undefined });
    } catch (error) {
      if (error instanceof ApiRequestError) {
        throw error;
      }
      return mockApi.updatePolicy(policyId, updates);
    }
  },
  async deletePolicy(policyId: number, actorUserId?: number | null) {
    try {
      return await requestJson(`/insurance/policies/${policyId}`, { method: 'DELETE' }, { actor_user_id: actorUserId ?? undefined });
    } catch (error) {
      if (error instanceof ApiRequestError) {
        throw error;
      }
      return mockApi.deletePolicy(policyId);
    }
  },
  async renewPolicy(
    policyId: number,
    payload?: { new_expiry_date: string; renewal_notes?: string | null },
    actorUserId?: number | null,
  ) {
    try {
      return await requestJson<import("./types").PolicyRenewResponse>(
        `/insurance/policies/${policyId}/renew`,
        {
          method: "POST",
          body: payload ? JSON.stringify(payload) : undefined,
        },
        { actor_user_id: actorUserId ?? undefined },
      );
    } catch {
      return mockApi.renewPolicy(policyId, payload);
    }
  },
  async sendPolicyRenewalSms(
    policyId: number,
    options?: { actorUserId?: number | null; loggedInUserName?: string | null },
  ): Promise<PolicyRenewalSmsResponse> {
    return await requestJson<PolicyRenewalSmsResponse>(
      `/insurance/policies/${policyId}/renewal-sms`,
      { method: "POST" },
      {
        actor_user_id: options?.actorUserId ?? undefined,
        logged_in_user_name: options?.loggedInUserName ?? undefined,
      },
    );
  },
  async listFollowups(organizationId: number, status?: string) {
    try {
      const data = await requestJson<any[]>('/insurance/followups', undefined, { organization_id: organizationId, status });
      // When backend returns an empty list in development, fall back to the mock store so UI still shows sample rows
      if (Array.isArray(data) && data.length === 0) {
        return mockApi.listFollowups(organizationId, status);
      }
      return data;
    } catch {
      return mockApi.listFollowups(organizationId, status);
    }
  },
  async createFollowup(input: any, organizationId: number, actorUserId?: number | null) {
    try {
      return await requestJson<any>('/insurance/followups', { method: 'POST', body: JSON.stringify(input) }, { organization_id: organizationId, actor_user_id: actorUserId ?? undefined });
    } catch {
      return mockApi.createFollowup(input, organizationId);
    }
  },
  async getFollowup(followupId: number) {
    try {
      return await requestJson<any>(`/insurance/followups/${followupId}`);
    } catch {
      return mockApi.getFollowup(followupId);
    }
  },
  async updateFollowup(followupId: number, updates: any, actorUserId?: number | null) {
    try {
      return await requestJson<any>(`/insurance/followups/${followupId}`, { method: 'PUT', body: JSON.stringify(updates) }, { actor_user_id: actorUserId ?? undefined });
    } catch {
      return mockApi.updateFollowup(followupId, updates);
    }
  },
  async deleteFollowup(followupId: number, actorUserId?: number | null) {
    try {
      return await requestJson(`/insurance/followups/${followupId}`, { method: 'DELETE' }, { actor_user_id: actorUserId ?? undefined });
    } catch {
      return mockApi.deleteFollowup(followupId);
    }
  },
  // Leads / demos
  async createLead(input: any) {
    return await requestJson('/insurance/leads', { method: 'POST', body: JSON.stringify(input) });
  },
  async patchLead(leadId: number, updates: any) {
    try {
      return await requestJson(`/insurance/leads/${leadId}`, { method: 'PATCH', body: JSON.stringify(updates) });
    } catch {
      return mockApi.patchLead(leadId, updates);
    }
  },
  async startLeadWorkflow(leadId: number, body: any) {
    return await requestJson(`/insurance/leads/${leadId}/follow-up-workflow`, { method: 'POST', body: JSON.stringify(body) });
  },
  async startPolicyWorkflow(policyId: number, body: any) {
    try {
      return await requestJson(`/insurance/policies/${policyId}/renewal-workflow`, { method: 'POST', body: JSON.stringify(body) });
    } catch {
      return mockApi.startPolicyWorkflow(policyId, body);
    }
  },
  async constructionDashboard(): Promise<ConstructionDashboard> {
    return mockApi.constructionDashboard();
  },
  async medicalDashboard(): Promise<MedicalDashboard> {
    return mockApi.medicalDashboard();
  },
  async previewCommand(command: string): Promise<CommandPreview> {
    return Promise.resolve(mockApi.simulateCommand(command));
  },
  async changePassword(input: { current_password: string; new_password: string }) {
    return await requestJson<{ detail: string }>("/auth/password", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  async getReminderConfigs(organizationId: number, entityType: string, entityId: number) {
    return await requestJson<ReminderConfigGroupListResponse>(
      `/reminders/config/${entityType}/${entityId}`,
      undefined,
      { organization_id: organizationId }
    );
  },
  async saveReminderSettings(input: ReminderSettingsSaveInput) {
    return await requestJson<ReminderConfigListResponse>("/reminders/config/settings", {
      method: "PUT",
      body: JSON.stringify(input),
    });
  },
  async createReminderConfigs(input: ReminderConfigCreateInput) {
    return await requestJson<ReminderConfigGroupListResponse>("/reminders/config", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  async updateReminderConfig(configId: number, input: ReminderConfigUpdateInput) {
    return await requestJson<ReminderConfigGroupRecord>(`/reminders/config/${configId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },
  async deleteReminderConfig(configId: number) {
    return await requestJson<{ message: string }>(`/reminders/config/${configId}`, {
      method: "DELETE",
    });
  },

  async listReminderModules() {
    return await requestJson<
      Array<{ id: string; name: string; supports_date: boolean; supports_workflow: boolean }>
    >("/reminders/modules");
  },

  async getReminderModuleSchema(module: string) {
    return await requestJson<{
      trigger_types: Array<{ key: string; label: string; type: string }>;
      workflow_events: Array<{ key: string; label: string }>;
      recipient_types: Array<{ id: string; label: string }>;
      supported_channels: string[];
      default_template?: string | null;
    }>(`/reminders/modules/${encodeURIComponent(module)}/schema`);
  },

  async listReminderChannels() {
    return await requestJson<string[]>("/reminders/channels");
  },

  async listReminderCatalogTemplates() {
    return await requestJson<
      Array<{
        id: string;
        name: string;
        channel: string;
        subject: string;
        body: string;
        module?: string | null;
      }>
    >("/reminders/templates");
  },

  async listGeneralReminders(params?: {
    module_key?: string;
    is_active?: boolean;
    trigger_type?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }) {
    return await requestJson<{
      items: GeneralReminderDefinitionDto[];
      total: number;
      limit: number;
      offset: number;
    }>("/general-reminders", undefined, {
      module_key: params?.module_key,
      is_active: params?.is_active,
      trigger_type: params?.trigger_type,
      q: params?.q,
      limit: params?.limit,
      offset: params?.offset,
    });
  },

  async getGeneralReminder(id: string) {
    return await requestJson<GeneralReminderDefinitionDto>(`/general-reminders/${encodeURIComponent(id)}`);
  },

  async createGeneralReminder(input: GeneralReminderUpsertDto) {
    return await requestJson<GeneralReminderDefinitionDto>("/general-reminders", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async updateGeneralReminder(id: string, input: Partial<GeneralReminderUpsertDto>) {
    return await requestJson<GeneralReminderDefinitionDto>(`/general-reminders/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    });
  },

  async deleteGeneralReminder(id: string) {
    return await requestJson<void>(`/general-reminders/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },

  async listNotifications(params?: { status?: string; limit?: number; offset?: number }) {
    return await requestJson<InAppNotificationListResponse>("/notifications", undefined, {
      status: params?.status,
      limit: params?.limit,
      offset: params?.offset,
    });
  },

  async getUnreadNotificationCount() {
    return await requestJson<UnreadCountResponse>("/notifications/unread-count");
  },

  async markNotificationRead(notificationId: number) {
    return await requestJson<InAppNotificationRecord>(`/notifications/${notificationId}/read`, {
      method: "PATCH",
    });
  },

  async markAllNotificationsRead() {
    return await requestJson<{ updated: number }>("/notifications/read-all", {
      method: "PATCH",
    });
  },

  async deleteNotification(notificationId: number) {
    return await requestJson<{ deleted: boolean }>(`/notifications/${notificationId}`, {
      method: "DELETE",
    });
  },
};
