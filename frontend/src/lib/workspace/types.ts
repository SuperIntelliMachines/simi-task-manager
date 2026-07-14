/** Shared SIMI workspace configuration — only title, org, nav, and routes differ per module. */

export type NavIconName =
  | "dashboard"
  | "file-plus"
  | "file-text"
  | "phone"
  | "clock"
  | "bell"
  | "list-todo"
  | "bot"
  | "clipboard"
  | "history-bell"
  | "building"
  | "users"
  | "shield"
  | "key"
  | "scroll";

export type WorkspaceNavLink = {
  type: "link";
  to: string;
  label: string;
  icon: NavIconName;
  end?: boolean;
  /** When set, item is shown only if the user has this permission. */
  permission?: string;
};

export type WorkspaceNavGroup = {
  type: "group";
  id: string;
  label: string;
  icon: NavIconName;
  children: WorkspaceNavLink[];
  /** Path prefixes that auto-expand this group. */
  openPrefixes: string[];
};

export type WorkspaceNavItem = WorkspaceNavLink | WorkspaceNavGroup;

export type WorkspaceConfig = {
  id: string;
  /**
   * Fixed sidebar organization title. When omitted, the live organization name
   * from session is used (Insurance / Claims / Construction / etc.).
   */
  organizationName?: string;
  /** Fixed sidebar subtitle. When omitted, derived from tenant key. */
  organizationSubtitle?: string;
  headerTitle: string;
  headerSubtitle: string;
  aiCardTitle: string;
  aiCardSubtitle: string;
  settingsPath: string;
  navigation: WorkspaceNavItem[];
  features: {
    /** Mount Insurance AI assistant panel when Ask AI is clicked. */
    insuranceAiPanel: boolean;
    /** Use insurance-specific refresh pipeline. */
    insuranceRefresh: boolean;
  };
};

export const SIMI_HEADER_TITLE = "SIMI AI Task Manager";
export const SIMI_HEADER_SUBTITLE = "AI-powered task management and workflow automation";
