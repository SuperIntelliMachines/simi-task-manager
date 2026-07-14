import { isClaimsOrganization } from "../auth/post-login";
import { PERMISSIONS } from "../auth/permissions";
import {
  ADMIN_WORKSPACE,
  CLAIMS_WORKSPACE,
  CONSTRUCTION_WORKSPACE,
  GENERIC_WORKSPACE,
  INSURANCE_WORKSPACE,
  MEDICAL_WORKSPACE,
} from "./configs";
import type { WorkspaceConfig } from "./types";

const isInsuranceTenant = (key?: string) => (key || "").includes("insurance");
const isConstructionTenant = (key?: string) => (key || "").includes("construction");
const isMedicalTenant = (key?: string) => (key || "").includes("medical");

function orgLooksLikeInsurance(organizationName?: string | null): boolean {
  return (organizationName || "").toLowerCase().includes("insur");
}

function isInsuranceRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/app/insurance") ||
    pathname.startsWith("/app/custom-reminders")
  );
}

export type ResolveWorkspaceInput = {
  pathname: string;
  tenantKey?: string;
  organizationName?: string | null;
  hasPermission: (permission: string) => boolean;
};

/**
 * Picks the shared workspace config for the current route/tenant.
 * New modules: add a config and a branch here — never a custom shell.
 *
 * Reminder Management lives under /app/reminders (and Claims equivalent) but
 * must NOT steal workspace selection — Insurance/Claims detection stays primary.
 */
export function resolveWorkspaceConfig(input: ResolveWorkspaceInput): WorkspaceConfig {
  const { pathname, tenantKey, organizationName, hasPermission } = input;

  if (pathname.startsWith("/master")) {
    return ADMIN_WORKSPACE;
  }

  if (isClaimsOrganization(organizationName) || tenantKey === "claims" || pathname.startsWith("/claims")) {
    return CLAIMS_WORKSPACE;
  }

  const insuranceContext =
    isInsuranceTenant(tenantKey) ||
    orgLooksLikeInsurance(organizationName) ||
    isInsuranceRoute(pathname);

  if (insuranceContext) {
    // Deep-linked Insurance routes keep Insurance chrome even while permissions hydrate.
    if (hasPermission(PERMISSIONS.insuranceView) || isInsuranceRoute(pathname)) {
      return INSURANCE_WORKSPACE;
    }
  }

  if (
    isConstructionTenant(tenantKey) ||
    (organizationName || "").toLowerCase().includes("construction")
  ) {
    return CONSTRUCTION_WORKSPACE;
  }

  if (
    isMedicalTenant(tenantKey) ||
    (organizationName || "").toLowerCase().includes("medical")
  ) {
    return MEDICAL_WORKSPACE;
  }

  return GENERIC_WORKSPACE;
}

export function formatOrgInitials(name: string): string {
  try {
    const parts = (name || "").split(/[^A-Za-z0-9]+/).filter(Boolean);
    if (parts.length === 0) return "SI";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  } catch {
    return "SI";
  }
}

export function formatTenantSubtitle(tenantKey?: string): string {
  try {
    const raw = (tenantKey || "").replace(/[-_]/g, " ");
    if (!raw) return "";
    return raw
      .split(" ")
      .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
      .join(" ");
  } catch {
    return "";
  }
}

export function resolveOrgDisplayName(input: {
  organizationName?: string | null;
  tenantLabel?: string | null;
  tenantKey?: string;
  workspace: WorkspaceConfig;
}): string {
  if (input.workspace.organizationName) return input.workspace.organizationName;
  try {
    if (input.organizationName?.trim()) return input.organizationName;
    if (
      input.tenantLabel?.trim() &&
      input.tenantLabel.toLowerCase() !== (input.tenantKey || "").toLowerCase()
    ) {
      return input.tenantLabel;
    }
  } catch {
    /* ignore */
  }
  if ((input.tenantKey || "").toLowerCase().includes("insur")) return "SIMI";
  if (input.workspace.id === "insurance") return "Insurance";
  return "Organization";
}
