import { ADMIN_CONSOLE_NAME } from "../auth/role-labels";
import { PERMISSIONS } from "../auth/permissions";
import {
  SIMI_HEADER_SUBTITLE,
  SIMI_HEADER_TITLE,
  type WorkspaceConfig,
  type WorkspaceNavGroup,
  type WorkspaceNavItem,
} from "./types";

const defaultFeatures = {
  insuranceAiPanel: false,
  insuranceRefresh: false,
} as const;

/** Generic Reminder Management — shared across Insurance / Generic / Claims workspaces. */
function remindersNavGroup(basePath: string): WorkspaceNavGroup {
  return {
    type: "group",
    id: "reminders",
    label: "Reminders",
    icon: "bell",
    openPrefixes: [basePath],
    children: [
      {
        type: "link",
        to: basePath,
        label: "Reminder List",
        icon: "list-todo",
        end: true,
        permission: PERMISSIONS.remindersView,
      },
      {
        type: "link",
        to: `${basePath}/create`,
        label: "Create Reminder",
        icon: "file-plus",
        permission: PERMISSIONS.remindersCreate,
      },
      {
        type: "link",
        to: `${basePath}/templates`,
        label: "Templates",
        icon: "file-text",
        permission: PERMISSIONS.remindersView,
      },
      {
        type: "link",
        to: `${basePath}/history`,
        label: "History",
        icon: "history-bell",
        permission: PERMISSIONS.remindersView,
      },
    ],
  };
}

const APP_REMINDERS_NAV = () => remindersNavGroup("/app/reminders");
const CLAIMS_REMINDERS_NAV = () => remindersNavGroup("/claims/reminder-management");

const genericBaseNav: WorkspaceNavItem[] = [
  { type: "link", to: "/app", label: "Dashboard", icon: "dashboard", end: true },
  { type: "link", to: "/app/tasks", label: "Tasks", icon: "list-todo", permission: PERMISSIONS.tasksView },
  { type: "link", to: "/app/agents", label: "AI Assistant", icon: "bot", permission: PERMISSIONS.agentsView },
  { type: "link", to: "/app/channels", label: "Channels", icon: "phone", permission: "channels:view" },
  APP_REMINDERS_NAV(),
];

/** Insurance — design standard for all SIMI workspaces. */
export const INSURANCE_WORKSPACE: WorkspaceConfig = {
  id: "insurance",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with renewals & follow-ups",
  settingsPath: "/app/settings",
  features: { insuranceAiPanel: true, insuranceRefresh: true },
  navigation: [
    { type: "link", to: "/app/insurance", label: "Dashboard", icon: "dashboard", end: true },
    {
      type: "group",
      id: "insurance",
      label: "Insurance",
      icon: "file-text",
      openPrefixes: [
        "/app/insurance/policies",
        "/app/insurance/demos",
        "/app/insurance/renewals",
        "/app/insurance/followups",
      ],
      children: [
        { type: "link", to: "/app/insurance/policies/create", label: "Add Policy Holder", icon: "file-plus", end: true },
        { type: "link", to: "/app/insurance/policies", label: "Policy List", icon: "file-text", end: true },
        { type: "link", to: "/app/insurance/demos/log", label: "Lead Follow-up", icon: "phone", end: true },
        { type: "link", to: "/app/insurance/renewals/upcoming", label: "Upcoming Renewals", icon: "clock", end: true },
        { type: "link", to: "/app/insurance/followups", label: "Follow-up Tracking", icon: "phone", end: true },
      ],
    },
    APP_REMINDERS_NAV(),
    { type: "link", to: "/app/custom-reminders", label: "Renewal Reminders", icon: "bell" },
  ],
};

export const CLAIMS_WORKSPACE: WorkspaceConfig = {
  id: "claims",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with service cases & reminders",
  settingsPath: "/claims/settings",
  features: { ...defaultFeatures },
  navigation: [
    { type: "link", to: "/claims/dashboard", label: "Dashboard", icon: "dashboard", end: true },
    { type: "link", to: "/claims/service-cases", label: "Service Cases", icon: "clipboard" },
    CLAIMS_REMINDERS_NAV(),
    { type: "link", to: "/claims/reminders", label: "Reminder Settings", icon: "clock" },
    { type: "link", to: "/claims/notifications", label: "Notification History", icon: "history-bell" },
  ],
};

export const ADMIN_WORKSPACE: WorkspaceConfig = {
  id: "admin",
  organizationName: ADMIN_CONSOLE_NAME,
  organizationSubtitle: "Platform governance",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with organizations & access",
  settingsPath: "/master/settings",
  features: { ...defaultFeatures },
  navigation: [
    { type: "link", to: "/master", label: "Dashboard", icon: "dashboard", end: true },
    { type: "link", to: "/master/organizations", label: "Organizations", icon: "building" },
    { type: "link", to: "/master/users", label: "Users", icon: "users" },
    { type: "link", to: "/master/roles", label: "Roles", icon: "shield" },
    { type: "link", to: "/master/permissions", label: "Permissions", icon: "key" },
    { type: "link", to: "/master/audit", label: "Audit Logs", icon: "scroll" },
  ],
};

export const CONSTRUCTION_WORKSPACE: WorkspaceConfig = {
  id: "construction",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with tasks & workflows",
  settingsPath: "/app/settings",
  features: { ...defaultFeatures },
  navigation: [
    ...genericBaseNav,
    { type: "link", to: "/app/construction", label: "Construction", icon: "dashboard" },
  ],
};

export const MEDICAL_WORKSPACE: WorkspaceConfig = {
  id: "medical",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with tasks & workflows",
  settingsPath: "/app/settings",
  features: { ...defaultFeatures },
  navigation: [
    ...genericBaseNav,
    { type: "link", to: "/app/medical-office", label: "Medical Office", icon: "file-text" },
  ],
};

export const GENERIC_WORKSPACE: WorkspaceConfig = {
  id: "generic",
  headerTitle: SIMI_HEADER_TITLE,
  headerSubtitle: SIMI_HEADER_SUBTITLE,
  aiCardTitle: "AI Assistant",
  aiCardSubtitle: "Ready to help with tasks & workflows",
  settingsPath: "/app/settings",
  features: { ...defaultFeatures },
  navigation: genericBaseNav,
};

/**
 * Register a new organization module by adding a WorkspaceConfig here and
 * resolving it in `resolveWorkspaceConfig`. No custom header/sidebar needed.
 */
export const WORKSPACE_REGISTRY = {
  insurance: INSURANCE_WORKSPACE,
  claims: CLAIMS_WORKSPACE,
  admin: ADMIN_WORKSPACE,
  construction: CONSTRUCTION_WORKSPACE,
  medical: MEDICAL_WORKSPACE,
  generic: GENERIC_WORKSPACE,
} as const;
