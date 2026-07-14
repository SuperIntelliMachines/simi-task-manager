const ROLE_DISPLAY_LABELS: Record<string, string> = {
  platform_admin: "Admin",
  org_admin: "Organization Admin",
  manager: "Manager",
  agent: "Agent",
  viewer: "Viewer",
  tenant_user: "User",
};

export const ADMIN_CONSOLE_NAME = "Admin Console";
export const ADMIN_CONSOLE_TITLE = `SIMI ${ADMIN_CONSOLE_NAME}`;
export const ADMIN_CONSOLE_EYEBROW = ADMIN_CONSOLE_NAME;

/** Maps internal RBAC role identifiers to user-facing labels only. */
export function formatRoleDisplayLabel(role: string | null | undefined): string {
  if (!role) return "—";
  const normalized = role.trim().toLowerCase();
  const mapped = ROLE_DISPLAY_LABELS[normalized];
  if (mapped) return mapped;
  return normalized
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
