import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { loadReminderChannelOptions } from "../reminders/channels";
import { getReminderModuleConfig, listReminderModules } from "./module-config";
import { reminderManagementApi } from "./service";
import type {
  ReminderDraft,
  ReminderHistoryFilters,
  ReminderListFilters,
  ReminderModuleKey,
  ReminderTemplate,
} from "./types";

const KEYS = {
  reminders: (filters: Partial<ReminderListFilters>) => ["reminder-management", "list", filters] as const,
  reminder: (id: string) => ["reminder-management", "detail", id] as const,
  templates: ["reminder-management", "templates"] as const,
  catalogTemplates: ["reminder-management", "catalog-templates"] as const,
  channels: ["reminder-management", "channels"] as const,
  history: (filters: Partial<ReminderHistoryFilters>) =>
    ["reminder-management", "history", filters] as const,
  modules: ["reminder-management", "modules"] as const,
  moduleConfig: (module: ReminderModuleKey) =>
    ["reminder-management", "module-config", module] as const,
};

export function useReminderModules() {
  return useQuery({
    queryKey: KEYS.modules,
    queryFn: () => listReminderModules(),
  });
}

export function useReminderModuleConfig(module: ReminderModuleKey) {
  return useQuery({
    queryKey: KEYS.moduleConfig(module),
    queryFn: () => getReminderModuleConfig(module),
    enabled: Boolean(module),
  });
}

export function useReminderChannels() {
  return useQuery({
    queryKey: KEYS.channels,
    queryFn: () => loadReminderChannelOptions(),
  });
}

export function useReminderCatalogTemplates() {
  return useQuery({
    queryKey: KEYS.catalogTemplates,
    queryFn: () => apiClient.listReminderCatalogTemplates(),
  });
}

export function useManagedReminders(filters: ReminderListFilters) {
  const page = filters.page ?? 0;
  const pageSize = filters.pageSize ?? 50;
  return useQuery({
    queryKey: KEYS.reminders(filters),
    queryFn: () =>
      reminderManagementApi.listReminders({
        ...filters,
        limit: pageSize,
        offset: page * pageSize,
      }),
  });
}

export function useManagedReminder(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.reminder(id ?? ""),
    queryFn: () => reminderManagementApi.getReminder(id!),
    enabled: Boolean(id),
  });
}

export function useCreateManagedReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draft: ReminderDraft) => reminderManagementApi.createReminder(draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-management"] });
    },
  });
}

export function useUpdateManagedReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: ReminderDraft }) =>
      reminderManagementApi.updateReminder(id, draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-management"] });
    },
  });
}

export function useToggleManagedReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      reminderManagementApi.setReminderEnabled(id, enabled),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-management"] });
    },
  });
}

export function useDeleteManagedReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reminderManagementApi.deleteReminder(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-management"] });
    },
  });
}

export function useTestManagedReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reminderManagementApi.testReminder(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-management", "history"] });
    },
  });
}

export function useReminderTemplates() {
  return useQuery({
    queryKey: KEYS.templates,
    queryFn: () => reminderManagementApi.listTemplates(),
  });
}

export function useCreateReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Omit<ReminderTemplate, "id" | "createdAt" | "updatedAt">) =>
      reminderManagementApi.createTemplate(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.templates });
    },
  });
}

export function useUpdateReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<ReminderTemplate> }) =>
      reminderManagementApi.updateTemplate(id, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.templates });
    },
  });
}

export function useDeleteReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reminderManagementApi.deleteTemplate(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.templates });
    },
  });
}

export function useReminderHistory(filters: Partial<ReminderHistoryFilters>) {
  return useQuery({
    queryKey: KEYS.history(filters),
    queryFn: () => reminderManagementApi.listHistory(filters),
  });
}
