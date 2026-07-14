/**
 * Display-only helpers for RBAC permission codes.
 * Does not change permission keys, APIs, or authorization — labels only.
 */

/** Optional friendly module names. Unknown modules title-case automatically. */
const MODULE_DISPLAY_LABELS: Record<string, string> = {
  admin: "Administration",
  users: "Users",
  organizations: "Organizations",
  claims: "Claims",
  insurance: "Insurance",
  reminders: "Reminders",
  leads: "Leads",
  bms: "BMS",
  agents: "AI Agents",
  tasks: "Tasks",
  channels: "Channels",
  templates: "Templates",
  approvals: "Approvals",
};

/** Preferred action order within a module group. */
const ACTION_SORT_ORDER = [
  "view",
  "create",
  "update",
  "delete",
  "assign",
  "close",
  "approve",
  "reject",
  "invite",
  "onboard",
  "process",
  "complete",
  "invoke",
  "test",
] as const;

function titleCaseToken(token: string): string {
  if (!token) return "";
  return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase();
}

function titleCaseKey(value: string): string {
  return value
    .trim()
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map(titleCaseToken)
    .join(" ");
}

/** Parse `module:action` codes. Falls back gracefully for unexpected shapes. */
export function parsePermissionCode(code: string): { module: string; action: string } {
  const trimmed = (code || "").trim();
  const colon = trimmed.indexOf(":");
  if (colon <= 0) {
    return { module: trimmed || "other", action: trimmed || "unknown" };
  }
  return {
    module: trimmed.slice(0, colon).toLowerCase(),
    action: trimmed.slice(colon + 1).toLowerCase() || "unknown",
  };
}

/** Human-readable module label (e.g. admin → Administration). */
export function formatPermissionModuleLabel(moduleOrCode: string): string {
  const moduleKey = moduleOrCode.includes(":")
    ? parsePermissionCode(moduleOrCode).module
    : moduleOrCode.trim().toLowerCase();
  if (MODULE_DISPLAY_LABELS[moduleKey]) return MODULE_DISPLAY_LABELS[moduleKey];
  // Short acronyms (hr, crm) read better fully uppercased.
  if (/^[a-z]{2,3}$/.test(moduleKey)) return moduleKey.toUpperCase();
  return titleCaseKey(moduleKey);
}

/** Human-readable action label (e.g. create → Create, follow_up → Follow Up). */
export function formatPermissionActionLabel(actionOrCode: string): string {
  const action = actionOrCode.includes(":")
    ? parsePermissionCode(actionOrCode).action
    : actionOrCode.trim().toLowerCase();
  return titleCaseKey(action);
}

/** Two-line style summary used in lists: module + action. */
export function formatPermissionDisplay(code: string): { module: string; action: string } {
  const parsed = parsePermissionCode(code);
  return {
    module: formatPermissionModuleLabel(parsed.module),
    action: formatPermissionActionLabel(parsed.action),
  };
}

export function comparePermissionActions(a: string, b: string): number {
  const ai = ACTION_SORT_ORDER.indexOf(a as (typeof ACTION_SORT_ORDER)[number]);
  const bi = ACTION_SORT_ORDER.indexOf(b as (typeof ACTION_SORT_ORDER)[number]);
  const aRank = ai === -1 ? ACTION_SORT_ORDER.length : ai;
  const bRank = bi === -1 ? ACTION_SORT_ORDER.length : bi;
  if (aRank !== bRank) return aRank - bRank;
  return a.localeCompare(b);
}

export type PermissionModuleGroup<T extends { code: string; module?: string }> = {
  moduleKey: string;
  moduleLabel: string;
  permissions: T[];
};

/**
 * Group permissions by module key derived from API `module` or code prefix.
 * New modules appear automatically — no UI registry required.
 */
export function groupPermissionsByModule<T extends { code: string; module?: string }>(
  permissions: T[],
): PermissionModuleGroup<T>[] {
  const map = new Map<string, T[]>();

  for (const permission of permissions) {
    const moduleKey = (permission.module || parsePermissionCode(permission.code).module).toLowerCase();
    const list = map.get(moduleKey) ?? [];
    list.push(permission);
    map.set(moduleKey, list);
  }

  return Array.from(map.entries())
    .map(([moduleKey, items]) => ({
      moduleKey,
      moduleLabel: formatPermissionModuleLabel(moduleKey),
      permissions: [...items].sort((a, b) =>
        comparePermissionActions(
          parsePermissionCode(a.code).action,
          parsePermissionCode(b.code).action,
        ),
      ),
    }))
    .sort((a, b) => a.moduleLabel.localeCompare(b.moduleLabel));
}
