import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { platformApi } from "./api";

export function usePlatformStats() {
  return useQuery({ queryKey: ["platform", "stats"], queryFn: () => platformApi.getStats() });
}

export function usePlatformOrganizations() {
  return useQuery({ queryKey: ["platform", "organizations"], queryFn: () => platformApi.listOrganizations() });
}

export function usePlatformOrganization(id: number | null) {
  return useQuery({
    queryKey: ["platform", "organizations", id],
    queryFn: () => platformApi.getOrganization(id!),
    enabled: id != null,
  });
}

export function usePlatformUsers() {
  return useQuery({ queryKey: ["platform", "users"], queryFn: async () => (await platformApi.listUsers()).users });
}

export function usePlatformRoles() {
  return useQuery({
    queryKey: ["platform", "roles"],
    queryFn: async () => (await platformApi.listRoles()).roles,
  });
}

export function usePlatformPermissions() {
  return useQuery({
    queryKey: ["platform", "permissions"],
    queryFn: async () => (await platformApi.listPermissions()).permissions,
  });
}

export function usePlatformAuditLogs(limit = 100) {
  return useQuery({
    queryKey: ["platform", "audit", limit],
    queryFn: async () => (await platformApi.listAuditLogs(limit)).audit_logs,
  });
}

export function useCreateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: platformApi.createOrganization,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "organizations"] });
      qc.invalidateQueries({ queryKey: ["platform", "stats"] });
    },
  });
}

export function useUpdateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => platformApi.updateOrganization(id, { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "organizations"] }),
  });
}

export function useDeleteOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: platformApi.deleteOrganization,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "organizations"] });
      qc.invalidateQueries({ queryKey: ["platform", "stats"] });
    },
  });
}

export function useCreatePlatformUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: platformApi.createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "users"] });
      qc.invalidateQueries({ queryKey: ["platform", "stats"] });
    },
  });
}

export function useUpdatePlatformUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...input
    }: {
      id: number;
      organization_id?: number;
      role?: string;
      is_active?: boolean;
    }) => platformApi.updateUser(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "users"] }),
  });
}

export function useResetPlatformUserPassword() {
  return useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) => platformApi.resetUserPassword(id, password),
  });
}

export function useCreatePlatformRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: platformApi.createRole,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "roles"] }),
  });
}

export function useUpdateRolePermissions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ roleId, codes }: { roleId: number; codes: string[] }) =>
      platformApi.updateRolePermissions(roleId, codes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "roles"] });
      qc.invalidateQueries({ queryKey: ["platform", "permissions"] });
    },
  });
}
