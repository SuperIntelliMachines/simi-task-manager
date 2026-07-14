export type PlatformStats = {
  total_organizations: number;
  total_users: number;
  active_users: number;
  active_organizations: number;
  total_agents: number;
  total_tasks: number;
  system_status: string;
};

export type PlatformUser = {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  organization_id: number;
  organization_name?: string | null;
  last_login_at?: string | null;
  created_at?: string | null;
};

export type PlatformRole = {
  id: number;
  name: string;
  description?: string | null;
  is_system: boolean;
  permissions: string[];
};

export type PlatformPermission = {
  id: number;
  module: string;
  permission: string;
  code: string;
  description?: string | null;
};

export type PlatformAuditLog = {
  id: number;
  source: "login_audit" | "audit_event";
  email?: string;
  success?: boolean;
  failure_reason?: string | null;
  ip_address?: string | null;
  organization_id?: number;
  event_type?: string;
  entity_type?: string;
  entity_id?: string;
  created_at?: string | null;
};
