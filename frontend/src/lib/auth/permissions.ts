/** Frontend permission helpers for SIMI RBAC. */

export function hasPermission(permissions: string[] | undefined, permission: string): boolean {
  return Boolean(permissions?.includes(permission));
}

export function hasAnyPermission(permissions: string[] | undefined, required: string[]): boolean {
  if (!permissions?.length) return false;
  return required.some((p) => permissions.includes(p));
}

export const PERMISSIONS = {
  insuranceView: "insurance:view",
  insuranceCreate: "insurance:create",
  insuranceUpdate: "insurance:update",
  insuranceDelete: "insurance:delete",
  remindersView: "reminders:view",
  remindersCreate: "reminders:create",
  remindersUpdate: "reminders:update",
  remindersDelete: "reminders:delete",
  leadsView: "leads:view",
  leadsCreate: "leads:create",
  tasksView: "tasks:view",
  tasksCreate: "tasks:create",
  agentsView: "agents:view",
  adminView: "admin:view",
  adminInvite: "admin:invite",
} as const;

export const ROUTE_PERMISSIONS: Record<string, string> = {
  "/app/tasks": PERMISSIONS.tasksView,
  "/app/insurance": PERMISSIONS.insuranceView,
  "/app/agents": PERMISSIONS.agentsView,
  "/app/channels": "channels:view",
  "/app/custom-reminders": PERMISSIONS.remindersView,
  "/app/reminders": PERMISSIONS.remindersView,
  "/claims/reminder-management": PERMISSIONS.remindersView,
  "/master": PERMISSIONS.adminView,
};
