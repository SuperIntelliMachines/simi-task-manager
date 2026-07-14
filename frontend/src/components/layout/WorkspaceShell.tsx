import React, { useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { InsuranceAiAssistantPanel } from "../insurance/insurance-ai-assistant-panel";
import { useToast } from "../ui/toast";
import { refreshInsuranceModuleData } from "../../lib/insurance/refresh-module-data";
import {
  formatOrgInitials,
  formatTenantSubtitle,
  resolveOrgDisplayName,
  resolveWorkspaceConfig,
} from "../../lib/workspace/resolve";
import type { WorkspaceConfig } from "../../lib/workspace/types";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

type WorkspaceShellProps = {
  /** Optional override; normally resolved from route + tenant. */
  workspace?: WorkspaceConfig;
};

/**
 * Shared SIMI application shell (Insurance design standard).
 * Every workspace — Insurance, Claims, Admin Console, and future orgs —
 * composes this shell. Only workspace config (title, org, nav) differs.
 */
export function WorkspaceShell({ workspace: workspaceOverride }: WorkspaceShellProps = {}) {
  const {
    tenantLabel,
    tenantKey,
    currentUser,
    currentUserName,
    organizationName,
    organizationId,
    refreshSession,
    signOut,
    hasPermission,
  } = useWorkbench();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const workspace = useMemo(
    () =>
      workspaceOverride ??
      resolveWorkspaceConfig({
        pathname: location.pathname,
        tenantKey,
        // Prefer display name; fall back to tenantLabel so Insurance orgs still
        // resolve while organizationName is hydrating / filtered.
        organizationName: organizationName || tenantLabel,
        hasPermission,
      }),
    [workspaceOverride, location.pathname, tenantKey, organizationName, tenantLabel, hasPermission],
  );

  const orgName = useMemo(
    () =>
      resolveOrgDisplayName({
        organizationName,
        tenantLabel,
        tenantKey,
        workspace,
      }),
    [organizationName, tenantLabel, tenantKey, workspace],
  );

  const orgSubtitle = useMemo(
    () => workspace.organizationSubtitle ?? formatTenantSubtitle(tenantKey),
    [workspace.organizationSubtitle, tenantKey],
  );

  const orgInitials = useMemo(() => formatOrgInitials(orgName), [orgName]);

  // Session hydration lives in WorkbenchProvider only. A second refresh here
  // raced with /me failures and could clear org state after Reminder route mounts.

  const handleLogout = async () => {
    await signOut();
  };

  const userEmail = currentUser?.email || currentUserName || "";
  const userDisplayName = useMemo(() => {
    if (!userEmail) return "User";
    const raw = userEmail.split("@")[0].split(/[._-]/)[0];
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }, [userEmail]);
  const userInitials = userEmail ? userEmail.split("@")[0].slice(0, 2).toUpperCase() : "U";

  async function handleRefresh() {
    if (isRefreshing) return;
    if (organizationId == null) {
      showToast("Organization is still loading. Please try again.", "error");
      return;
    }
    setIsRefreshing(true);
    console.info("[Refresh] Refresh button clicked", {
      organizationId,
      module: tenantKey,
      workspace: workspace.id,
    });

    try {
      if (workspace.features.insuranceRefresh) {
        await refreshInsuranceModuleData(queryClient, organizationId);
      } else {
        await queryClient.refetchQueries({ type: "active" });
      }
      await refreshSession();
      showToast("Data refreshed successfully.", "success");
    } catch (error) {
      console.error("[Refresh] Refresh failed", error);
      showToast("Failed to refresh data.", "error");
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div
      className={`min-h-screen text-foreground relative gyantra-bg ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}
    >
      <div className="absolute inset-0 -z-30 bg-background" />

      <AppHeader
        workspace={workspace}
        orgInitials={orgInitials}
        onAskAi={() => setAiAssistantOpen(true)}
        onRefresh={() => void handleRefresh()}
        isRefreshing={isRefreshing}
      />

      {workspace.features.insuranceAiPanel && organizationId != null ? (
        <InsuranceAiAssistantPanel
          open={aiAssistantOpen}
          organizationId={organizationId}
          onClose={() => setAiAssistantOpen(false)}
        />
      ) : null}

      <div className="w-full px-4 py-6">
        <AppSidebar
          workspace={workspace}
          orgName={orgName}
          orgSubtitle={orgSubtitle}
          orgInitials={orgInitials}
          collapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed((s) => !s)}
          hasPermission={hasPermission}
          userDisplayName={userDisplayName}
          userEmail={userEmail || tenantKey || ""}
          userInitials={userInitials}
          onLogout={() => void handleLogout()}
        />

        <main
          className={`pb-10 overflow-y-auto h-[calc(100vh-56px)] pl-4 ${
            sidebarCollapsed ? "lg:pl-[88px]" : "lg:pl-[256px]"
          }`}
        >
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

/** Alias matching the suggested AppLayout name. */
export const AppLayout = WorkspaceShell;
