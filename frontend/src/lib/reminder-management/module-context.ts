/**
 * Resolve Reminder Management module context from the current workspace.
 *
 * When Reminder Management is opened inside a module workspace (Insurance,
 * Claims, Inventory, …), module_key is known and the selector is locked.
 * When opened from a global/generic workspace, the user must pick a module.
 *
 * Add new modules here only — do not scatter workspace→module maps in UI.
 */

import { useMemo } from "react";
import { useLocation } from "react-router-dom";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { resolveWorkspaceConfig } from "../workspace/resolve";

/**
 * Workspace config `id` → reminder definition `module_key`.
 * Keys must match `WorkspaceConfig.id`; values must match resolver module ids
 * from GET /reminders/modules (e.g. policy, claims).
 */
export const WORKSPACE_TO_REMINDER_MODULE: Readonly<Record<string, string>> = {
  insurance: "policy",
  claims: "claims",
  inventory: "inventory",
};

/**
 * Optional route-prefix hints for workspaces that may not be fully registered yet
 * (e.g. Inventory). Evaluated only when workspace id has no mapping.
 */
const PATH_PREFIX_TO_REMINDER_MODULE: ReadonlyArray<{ prefix: string; moduleKey: string }> = [
  { prefix: "/claims", moduleKey: "claims" },
  { prefix: "/app/insurance", moduleKey: "policy" },
  { prefix: "/app/inventory", moduleKey: "inventory" },
  { prefix: "/inventory", moduleKey: "inventory" },
];

export type ReminderModuleContext = {
  /** Reminder definition module_key when implied by workspace/route; null if user must choose. */
  moduleKey: string | null;
  /** When true, hide/lock the Module selector and always send this module_key. */
  locked: boolean;
  /** Workspace id used for the resolution (for debugging / labels). */
  workspaceId: string;
};

export function resolveReminderModuleContext(input: {
  workspaceId: string;
  pathname?: string;
}): ReminderModuleContext {
  const fromWorkspace = WORKSPACE_TO_REMINDER_MODULE[input.workspaceId];
  if (fromWorkspace) {
    return {
      moduleKey: fromWorkspace,
      locked: true,
      workspaceId: input.workspaceId,
    };
  }

  const pathname = input.pathname || "";
  for (const entry of PATH_PREFIX_TO_REMINDER_MODULE) {
    if (pathname === entry.prefix || pathname.startsWith(`${entry.prefix}/`)) {
      return {
        moduleKey: entry.moduleKey,
        locked: true,
        workspaceId: input.workspaceId,
      };
    }
  }

  return {
    moduleKey: null,
    locked: false,
    workspaceId: input.workspaceId,
  };
}

/** Hook: current Reminder Management module context for Create/Edit (and filters). */
export function useReminderModuleContext(): ReminderModuleContext {
  const { pathname } = useLocation();
  const { tenantKey, organizationName, tenantLabel, hasPermission } = useWorkbench();

  return useMemo(() => {
    const workspace = resolveWorkspaceConfig({
      pathname,
      tenantKey,
      organizationName: organizationName || tenantLabel,
      hasPermission,
    });
    return resolveReminderModuleContext({
      workspaceId: workspace.id,
      pathname,
    });
  }, [pathname, tenantKey, organizationName, tenantLabel, hasPermission]);
}
