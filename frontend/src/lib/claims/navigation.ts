/** Claims workspace navigation — sourced from the shared workspace registry. */
import { CLAIMS_WORKSPACE } from "../workspace/configs";
import type { WorkspaceNavLink } from "../workspace/types";

export type ClaimsNavItem = {
  to: string;
  label: string;
  end?: boolean;
  icon: "dashboard" | "service-cases" | "reminders" | "notifications";
};

const ICON_MAP: Record<string, ClaimsNavItem["icon"]> = {
  dashboard: "dashboard",
  clipboard: "service-cases",
  clock: "reminders",
  "history-bell": "notifications",
};

/** Sidebar items only. Settings stays in the shared AppShell footer. */
export const CLAIMS_NAV_ITEMS: readonly ClaimsNavItem[] = CLAIMS_WORKSPACE.navigation
  .filter((item): item is WorkspaceNavLink => item.type === "link")
  .map((item) => ({
    to: item.to,
    label: item.label,
    end: item.end,
    icon: ICON_MAP[item.icon] ?? "dashboard",
  }));

export const CLAIMS_SETTINGS_PATH = CLAIMS_WORKSPACE.settingsPath;
export const CLAIMS_WORKSPACE_NAME = "Claims";
