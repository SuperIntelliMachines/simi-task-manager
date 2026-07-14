import { createBrowserRouter, redirect, Navigate } from "react-router-dom";

import { AppShell } from "../components/layout/app-shell";
import { LoginPage } from "../pages/login";
import { ForgotPasswordPage } from "../pages/forgot-password";
import { ResetPasswordPage } from "../pages/reset-password";
import { LOGIN_PATH } from "../lib/auth/routes";
import { isClaimsOrganization, resolvePostLoginPath } from "../lib/auth/post-login";
import { ClaimsDashboardPage } from "../pages/claims/dashboard";
import { ClaimsServiceCasesPage } from "../pages/claims/service-cases";
import { ClaimsRemindersPage } from "../pages/claims/reminders";
import { ClaimsNotificationsPage } from "../pages/claims/notifications";
import { ClaimsSettingsPage } from "../pages/claims/settings";
import {
  CreateReminderPage,
  ReminderHistoryPage,
  ReminderListPage,
  ReminderTemplatesPage,
} from "../pages/reminders";
import { PlatformDashboardPage } from "../pages/platform/dashboard";
import { PlatformOrganizationsPage } from "../pages/platform/organizations";
import { PlatformOrganizationDetailsPage } from "../pages/platform/organization-details";
import { PlatformUsersPage } from "../pages/platform/users";
import { PlatformRolesPage } from "../pages/platform/roles";
import { PlatformPermissionsPage } from "../pages/platform/permissions";
import { PlatformAuditLogsPage } from "../pages/platform/audit-logs";
import { PlatformSettingsPage } from "../pages/platform/settings";
import { AgentsPage } from "../pages/agents";
import { ChannelsPage } from "../pages/channels";
import { ConstructionPage } from "../pages/construction";
import { HomePage } from "../pages/home";
import { InsurancePage } from "../pages/insurance";
import { PoliciesListPage } from "../pages/insurance/policies-list";
import { CreatePolicyPage } from "../pages/insurance/create-policy";
import { PolicyDetailsPage } from "../pages/insurance/policy-details";
import { EditPolicyPage } from "../pages/insurance/edit-policy";
import { UpcomingRenewalsPage } from "../pages/insurance/upcoming-renewals";
import { LapsedPoliciesPage } from "../pages/insurance/expired-policies";
import { RenewalHistoryPage } from "../pages/insurance/renewal-history";
import { ReminderTimelinePage } from "../pages/insurance/reminder-timeline";
import { LeadFollowupPage } from "../pages/insurance/log-demo";
import { CreateLeadPage } from "../pages/insurance/create-lead";
import { FollowupTrackingPage } from "../pages/insurance/followup-tracking";
import { LeadDetailsPage } from "../pages/insurance/lead-details";
import { InterestedPage } from "../pages/insurance/status-interested";
import { NotInterestedPage } from "../pages/insurance/status-not-interested";
import { FollowUpLaterPage } from "../pages/insurance/status-follow-up-later";
import { AssignedPoliciesPage } from "../pages/insurance/assigned-policies";
import { EscalatedRenewalsPage } from "../pages/insurance/escalated-renewals";
import { PendingActionsPage } from "../pages/insurance/pending-actions";
import { CustomRemindersPage } from "../pages/insurance/custom-reminders";
import { MedicalOfficePage } from "../pages/medical-office";
import { SettingsPage } from "../pages/settings";
import { TasksPage } from "../pages/tasks";
import { NotificationsPage } from "../pages/notifications";

export const router = createBrowserRouter([
  { path: "/", element: <LoginPage /> },
  { path: LOGIN_PATH, element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/reset-password", element: <ResetPasswordPage /> },
  { path: "/master-login", loader: () => redirect(LOGIN_PATH) },
  {
    path: "/master",
    element: <AppShell />,
    loader: async () => {
      try {
        const token = localStorage.getItem("atm:token");
        if (!token) return redirect(LOGIN_PATH);
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return redirect(LOGIN_PATH);
        const me = await res.json();
        const permissions = me.permissions ?? [];
        const role = me.role ?? "";
        if (resolvePostLoginPath({ organization_name: me.organization_name, role, permissions }) !== "/master") {
          return redirect("/app");
        }
        return null;
      } catch {
        return redirect(LOGIN_PATH);
      }
    },
    children: [
      { index: true, element: <PlatformDashboardPage /> },
      { path: "organizations", element: <PlatformOrganizationsPage /> },
      { path: "organizations/:organizationId", element: <PlatformOrganizationDetailsPage /> },
      { path: "users", element: <PlatformUsersPage /> },
      { path: "roles", element: <PlatformRolesPage /> },
      { path: "permissions", element: <PlatformPermissionsPage /> },
      { path: "audit", element: <PlatformAuditLogsPage /> },
      { path: "settings", element: <PlatformSettingsPage /> },
      { path: "notifications", element: <NotificationsPage /> },
    ],
  },
  {
    path: "/claims",
    element: <AppShell />,
    loader: async () => {
      try {
        const token = localStorage.getItem("atm:token");
        if (!token) return redirect(LOGIN_PATH);
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return redirect(LOGIN_PATH);
        const me = await res.json();
        const permissions = me.permissions ?? [];
        const role = me.role ?? "";
        const path = resolvePostLoginPath({
          organization_name: me.organization_name,
          role,
          permissions,
        });
        if (!isClaimsOrganization(me.organization_name)) {
          return redirect(path === "/claims/dashboard" ? "/app" : path);
        }
        return null;
      } catch {
        return redirect(LOGIN_PATH);
      }
    },
    children: [
      { index: true, element: <Navigate to="/claims/dashboard" replace /> },
      { path: "dashboard", element: <ClaimsDashboardPage /> },
      { path: "service-cases", element: <ClaimsServiceCasesPage /> },
      { path: "reminder-management", element: <ReminderListPage /> },
      { path: "reminder-management/create", element: <CreateReminderPage /> },
      { path: "reminder-management/templates", element: <ReminderTemplatesPage /> },
      { path: "reminder-management/history", element: <ReminderHistoryPage /> },
      { path: "reminder-management/:reminderId/edit", element: <CreateReminderPage /> },
      { path: "reminders", element: <ClaimsRemindersPage /> },
      { path: "notifications", element: <ClaimsNotificationsPage /> },
      { path: "settings", element: <ClaimsSettingsPage /> },
    ],
  },
  {
    path: "/app",
    element: <AppShell />,
    // loader runs before entering /app and its children. If the user is not
    // authenticated, redirect them to the login page.
    loader: async () => {
      try {
        const token = localStorage.getItem("atm:token");
        if (!token) return redirect(LOGIN_PATH);
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return redirect(LOGIN_PATH);
        const me = await res.json();
        if (isClaimsOrganization(me.organization_name)) {
          return redirect("/claims/dashboard");
        }
        return null;
      } catch (e) {
        return redirect(LOGIN_PATH);
      }
    },
    children: [
      { index: true, element: <IndexRouteRedirect /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "agents", element: <AgentsPage /> },
      { path: "channels", element: <ChannelsPage /> },
      { path: "reminders", element: <ReminderListPage /> },
      { path: "reminders/create", element: <CreateReminderPage /> },
      { path: "reminders/templates", element: <ReminderTemplatesPage /> },
      { path: "reminders/history", element: <ReminderHistoryPage /> },
      { path: "reminders/:reminderId/edit", element: <CreateReminderPage /> },
    { path: "insurance", element: <InsurancePage /> },
    { path: "insurance/policies", element: <PoliciesListPage /> },
    { path: "insurance/policies/create", element: <CreatePolicyPage /> },
    { path: "insurance/policies/:policyId", element: <PolicyDetailsPage /> },
    { path: "insurance/policies/:policyId/edit", element: <EditPolicyPage /> },
    { path: "insurance/leads/new", element: <CreateLeadPage /> },
    { path: "insurance/renewals", element: <Navigate to="/app/insurance/policies?filter=expiring_soon" replace /> },
    { path: "insurance/renewals/upcoming", element: <UpcomingRenewalsPage /> },
    { path: "insurance/renewals/lapsed", element: <LapsedPoliciesPage /> },
    { path: "insurance/renewals/history", element: <RenewalHistoryPage /> },
    { path: "insurance/renewals/reminders", element: <ReminderTimelinePage /> },
    { path: "insurance/demos/log", element: <LeadFollowupPage /> },
    { path: "insurance/followups", element: <FollowupTrackingPage /> },
    { path: "insurance/followups/:followupId", element: <LeadDetailsPage /> },
    { path: "insurance/followups/interested", element: <InterestedPage /> },
    { path: "insurance/followups/not-interested", element: <NotInterestedPage /> },
    { path: "insurance/followups/follow-up-later", element: <FollowUpLaterPage /> },
    { path: "insurance/followups/renewed", element: <Navigate to="/app/insurance/followups" replace /> },
    { path: "insurance/agents/assigned", element: <AssignedPoliciesPage /> },
    { path: "insurance/renewals/escalated", element: <EscalatedRenewalsPage /> },
    { path: "insurance/pending-actions", element: <PendingActionsPage /> },
      { path: "custom-reminders", element: <CustomRemindersPage /> },
      { path: "construction", element: <ConstructionPage /> },
      { path: "medical-office", element: <MedicalOfficePage /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);

function IndexRouteRedirect() {
  try {
    const orgName = localStorage.getItem("atm:organizationName") || localStorage.getItem("atm:tenant") || "";
    const permissions = JSON.parse(localStorage.getItem("atm:permissions") || "[]") as string[];

    const path = resolvePostLoginPath({ organization_name: orgName, permissions });
    if (path === "/master") {
      return <Navigate to="/master" replace />;
    }
    if (path === "/claims/dashboard" || isClaimsOrganization(orgName)) {
      return <Navigate to="/claims/dashboard" replace />;
    }

    const key = orgName.toLowerCase();
    if (key.includes("insur") || path === "/app/insurance") {
      return <Navigate to="/app/insurance" replace />;
    }
  } catch {
    // ignore
  }
  return <HomePage />;
}
