import type { CustomerRecord } from "../api/types";
import type {
  PlatformAuditLog,
  PlatformPermission,
  PlatformRole,
  PlatformStats,
  PlatformUser,
} from "./types";

const API_BASE = "/api/v1";

export type OrganizationDeleteDependency = {
  label: string;
  count: number;
};

export type OrganizationDeleteBlockedPayload = {
  error: "organization_has_dependencies";
  message: string;
  dependencies: OrganizationDeleteDependency[];
};

export class OrganizationDeleteBlockedError extends Error {
  readonly status = 409;
  readonly errorCode = "organization_has_dependencies" as const;
  readonly dependencies: OrganizationDeleteDependency[];

  constructor(message: string, dependencies: OrganizationDeleteDependency[]) {
    super(message);
    this.name = "OrganizationDeleteBlockedError";
    this.dependencies = dependencies;
  }
}

function authHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem("atm:token");
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    // ignore
  }
  return {};
}

function isOrganizationDeleteBlockedPayload(value: unknown): value is OrganizationDeleteBlockedPayload {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return (
    record.error === "organization_has_dependencies" &&
    typeof record.message === "string" &&
    Array.isArray(record.dependencies)
  );
}

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) return record.message;
    if (typeof record.detail === "string" && record.detail.trim()) return record.detail;
  }
  return fallback;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // ignore
    }

    const detail = body && typeof body === "object" ? (body as { detail?: unknown }).detail : undefined;
    if (response.status === 409 && isOrganizationDeleteBlockedPayload(detail)) {
      throw new OrganizationDeleteBlockedError(
        detail.message,
        detail.dependencies.map((item) => ({
          label: String(item.label),
          count: Number(item.count) || 0,
        })),
      );
    }

    throw new Error(formatErrorDetail(detail, `Request failed (${response.status})`));
  }
  return (await response.json()) as T;
}

export const platformApi = {
  getStats(): Promise<PlatformStats> {
    return requestJson<PlatformStats>("/admin/platform/stats");
  },
  listOrganizations(): Promise<CustomerRecord[]> {
    return requestJson<CustomerRecord[]>("/admin/customers");
  },
  createOrganization(input: { name: string }): Promise<CustomerRecord> {
    return requestJson<CustomerRecord>("/admin/customers", { method: "POST", body: JSON.stringify(input) });
  },
  updateOrganization(id: number, input: { name: string }): Promise<CustomerRecord> {
    return requestJson<CustomerRecord>(`/admin/customers/${id}`, { method: "PATCH", body: JSON.stringify(input) });
  },
  deleteOrganization(id: number): Promise<{ detail: string }> {
    return requestJson(`/admin/customers/${id}`, { method: "DELETE" });
  },
  getOrganization(id: number): Promise<CustomerRecord> {
    return requestJson<CustomerRecord>(`/admin/customers/${id}`);
  },
  listUsers(): Promise<{ users: PlatformUser[] }> {
    return requestJson("/admin/users");
  },
  createUser(input: {
    email: string;
    password: string;
    organization_id: number;
    role: string;
  }): Promise<PlatformUser> {
    return requestJson("/admin/users", { method: "POST", body: JSON.stringify(input) });
  },
  updateUser(
    id: number,
    input: { organization_id?: number; role?: string; is_active?: boolean },
  ): Promise<PlatformUser> {
    return requestJson(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(input) });
  },
  resetUserPassword(id: number, newPassword: string): Promise<{ detail: string }> {
    return requestJson(`/admin/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    });
  },
  inviteUser(input: { email: string; password: string; tenant: string }): Promise<{ invite_path: string }> {
    return requestJson("/admin/invite", { method: "POST", body: JSON.stringify(input) });
  },
  listRoles(): Promise<{ roles: PlatformRole[] }> {
    return requestJson("/admin/roles");
  },
  createRole(input: { name: string; description?: string }): Promise<PlatformRole> {
    return requestJson("/admin/roles", { method: "POST", body: JSON.stringify(input) });
  },
  updateRolePermissions(roleId: number, permissionCodes: string[]): Promise<PlatformRole> {
    return requestJson(`/admin/roles/${roleId}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ permission_codes: permissionCodes }),
    });
  },
  listPermissions(): Promise<{ permissions: PlatformPermission[] }> {
    return requestJson("/admin/permissions");
  },
  listAuditLogs(limit = 100): Promise<{ audit_logs: PlatformAuditLog[] }> {
    return requestJson(`/admin/audit?limit=${limit}`);
  },
};
