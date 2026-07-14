/**
 * Resolve the Reminder Management base path for the current workspace tree.
 * Claims orgs live under /claims; all other workspaces use /app.
 */
export function getRemindersBasePath(pathname: string): string {
  if (pathname.startsWith("/claims")) return "/claims/reminder-management";
  return "/app/reminders";
}

export function remindersPath(base: string, segment: "" | "create" | "templates" | "history" | string = "") {
  if (!segment) return base;
  if (segment === "create" || segment === "templates" || segment === "history") {
    return `${base}/${segment}`;
  }
  return `${base}/${segment}`;
}
