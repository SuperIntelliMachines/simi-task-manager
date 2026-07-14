import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  ChannelConnectionInput,
  NotificationPreferenceRecord,
  TaskCreateInput,
  TaskFilters,
  TaskPatchInput,
} from "./types";

export function useTasks(filters: TaskFilters | null) {
  return useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => apiClient.listTasks(filters!),
    enabled: filters != null && filters.organizationId != null && filters.organizationId > 0,
  });
}

export function useCreateTask(filters: TaskFilters | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaskCreateInput) => apiClient.createTask(payload),
    onSuccess: () => {
      if (filters) {
        queryClient.invalidateQueries({ queryKey: ["tasks", filters] });
      }
    },
  });
}

export function usePatchTask(filters: TaskFilters | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: number; payload: TaskPatchInput }) => apiClient.patchTask(taskId, payload),
    onSuccess: () => {
      if (filters) {
        queryClient.invalidateQueries({ queryKey: ["tasks", filters] });
      }
    },
  });
}

export function useCompleteTask(filters: TaskFilters | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, actorUserId }: { taskId: number; actorUserId?: number | null }) =>
      apiClient.completeTask(taskId, actorUserId),
    onSuccess: () => {
      if (filters) {
        queryClient.invalidateQueries({ queryKey: ["tasks", filters] });
      }
    },
  });
}

export function useSnoozeTask(filters: TaskFilters | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, dueAt, actorUserId }: { taskId: number; dueAt: string; actorUserId?: number | null }) =>
      apiClient.snoozeTask(taskId, dueAt, actorUserId),
    onSuccess: () => {
      if (filters) {
        queryClient.invalidateQueries({ queryKey: ["tasks", filters] });
      }
    },
  });
}

export function useApprovalRequests(organizationId: number | null) {
  return useQuery({
    queryKey: ["approval-requests", organizationId],
    queryFn: () => apiClient.listApprovalRequests(organizationId!),
    enabled: organizationId != null,
  });
}

export function useChannelConnections(organizationId: number | null) {
  return useQuery({
    queryKey: ["channel-connections", organizationId],
    queryFn: () => apiClient.listChannelConnections(organizationId!),
    enabled: organizationId != null,
  });
}

export function useUpsertChannelConnection(organizationId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChannelConnectionInput) => apiClient.upsertChannelConnection(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channel-connections", organizationId] }),
  });
}

export function useSendChannelTestMessage(organizationId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ connectionId, recipient, text }: { connectionId: number; recipient: string; text: string }) =>
      apiClient.sendChannelTestMessage(connectionId, recipient, text),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channel-connections", organizationId] }),
  });
}

export function useNotificationPreferences(organizationId: number | null) {
  return useQuery({
    queryKey: ["notification-preferences", organizationId],
    queryFn: () => apiClient.listNotificationPreferences(organizationId!),
    enabled: organizationId != null,
  });
}

export function useUpdateNotificationPreference(organizationId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ preferenceId, updates }: { preferenceId: number; updates: Partial<NotificationPreferenceRecord> }) =>
      apiClient.updateNotificationPreference(preferenceId, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-preferences", organizationId] }),
  });
}

export function useInsuranceDashboard(organizationId: number | null) {
  return useQuery({
    queryKey: ["insurance-dashboard", organizationId],
    queryFn: () => apiClient.insuranceDashboard(organizationId as number),
    enabled: organizationId != null,
  });
}

export function useListPolicies(organizationId: number | null, status?: string) {
  return useQuery({
    queryKey: ["insurance-policies", organizationId, status],
    queryFn: () => apiClient.listPolicies(organizationId as number, status),
    enabled: organizationId != null,
  });
}

export function useGetPolicy(policyId?: number) {
  return useQuery({
    queryKey: ["insurance-policy", policyId],
    queryFn: () => (policyId ? apiClient.getPolicy(policyId) : Promise.resolve(null)),
    enabled: !!policyId,
  });
}

export function useReminderConfigs(
  organizationId: number | null | undefined,
  entityType: string,
  entityId?: number
) {
  return useQuery({
    queryKey: ["reminder-configs", organizationId, entityType, entityId],
    queryFn: () => apiClient.getReminderConfigs(organizationId!, entityType, entityId!),
    enabled: organizationId != null && entityId != null && entityId >= 0,
  });
}

export function useCreatePolicy(organizationId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => {
      if (organizationId == null) {
        return Promise.reject(new Error("Your organization could not be loaded. Please refresh the page and try again."));
      }
      return apiClient.createPolicy({ ...payload, organization_id: organizationId });
    },
    onSuccess: () => {
      if (organizationId != null) {
        qc.invalidateQueries({ queryKey: ["insurance-policies", organizationId] });
        qc.invalidateQueries({ queryKey: ["insurance-dashboard", organizationId] });
      }
    },
  });
}

export function useUpdatePolicy(organizationId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ policyId, updates }: { policyId: number; updates: any }) => apiClient.updatePolicy(policyId, updates),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["insurance-policies", organizationId] });
      qc.invalidateQueries({ queryKey: ["insurance-policy", variables.policyId] });
      qc.invalidateQueries({ queryKey: ["insurance-dashboard", organizationId] });
      qc.invalidateQueries({
        queryKey: ["reminder-configs", organizationId, "policy", variables.policyId],
      });
    },
  });
}

export function useDeletePolicy(organizationId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (policyId: number) => apiClient.deletePolicy(policyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insurance-policies", organizationId] }),
  });
}

export function useRenewPolicy(organizationId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      policyId,
      newExpiryDate,
      renewalNotes,
      actorUserId,
    }: {
      policyId: number;
      newExpiryDate?: string;
      renewalNotes?: string | null;
      actorUserId?: number | null;
    }) =>
      apiClient.renewPolicy(
        policyId,
        newExpiryDate
          ? {
              new_expiry_date: new Date(newExpiryDate).toISOString(),
              renewal_notes: renewalNotes ?? null,
            }
          : undefined,
        actorUserId,
      ),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["insurance-policies", organizationId] });
      qc.invalidateQueries({ queryKey: ["insurance-dashboard", organizationId] });
      qc.invalidateQueries({ queryKey: ["insurance-policy", variables.policyId] });
    },
  });
}

export function useListFollowups(organizationId: number | null, status?: string) {
  return useQuery({
    queryKey: ["insurance-followups", organizationId, status],
    queryFn: () => apiClient.listFollowups(organizationId!, status),
    enabled: organizationId != null,
  });
}

export function useCreateFollowup(organizationId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: any) => apiClient.createFollowup(payload, organizationId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insurance-followups", organizationId] });
      qc.invalidateQueries({ queryKey: ["insurance-dashboard", organizationId] });
    },
  });
}

export function useGetFollowup(followupId?: number) {
  return useQuery({
    queryKey: ["insurance-followup", followupId],
    queryFn: () => (followupId ? apiClient.getFollowup(followupId) : Promise.resolve(null)),
    enabled: !!followupId,
  });
}

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: any) => apiClient.createLead(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insurance-dashboard"] });
      qc.invalidateQueries({ queryKey: ["insurance-followups"] });
    },
  });
}

export function usePatchLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, updates }: { leadId: number; updates: any }) => apiClient.patchLead(leadId, updates),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["insurance-dashboard"] });
      qc.invalidateQueries({ queryKey: ["insurance-followups"] });
      qc.invalidateQueries({ queryKey: ["insurance-followup", variables.leadId] });
    },
  });
}

export function useStartLeadWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, body }: { leadId: number; body: any }) => apiClient.startLeadWorkflow(leadId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insurance-dashboard"] });
      qc.invalidateQueries({ queryKey: ["insurance-followups"] });
    },
  });
}

export function useStartPolicyWorkflow() {
  return useMutation({
    mutationFn: ({ policyId, body }: { policyId: number; body: any }) => apiClient.startPolicyWorkflow(policyId, body),
  });
}

export function useConstructionDashboard() {
  return useQuery({
    queryKey: ["construction-dashboard"],
    queryFn: () => apiClient.constructionDashboard(),
  });
}

export function useMedicalDashboard() {
  return useQuery({
    queryKey: ["medical-dashboard"],
    queryFn: () => apiClient.medicalDashboard(),
  });
}

export function useCommandPreview() {
  return useMutation({
    mutationFn: (command: string) => apiClient.previewCommand(command),
  });
}

const NOTIFICATIONS_KEY = ["notifications"] as const;
const UNREAD_COUNT_KEY = ["notifications", "unread-count"] as const;

export function useNotifications(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: [...NOTIFICATIONS_KEY, params],
    queryFn: () => apiClient.listNotifications(params),
    refetchInterval: 30_000,
  });
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: UNREAD_COUNT_KEY,
    queryFn: () => apiClient.getUnreadNotificationCount(),
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: number) => apiClient.markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
}

export function useDeleteNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: number) => apiClient.deleteNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
}
