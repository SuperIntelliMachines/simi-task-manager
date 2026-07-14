import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { getNavIcon } from "../../lib/workspace/nav-icons";
import type { WorkspaceConfig, WorkspaceNavGroup, WorkspaceNavItem } from "../../lib/workspace/types";
import { SidebarFooter } from "./SidebarFooter";

type AppSidebarProps = {
  workspace: WorkspaceConfig;
  orgName: string;
  orgSubtitle: string;
  orgInitials: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  hasPermission: (permission: string) => boolean;
  userDisplayName: string;
  userEmail: string;
  userInitials: string;
  onLogout: () => void;
};

function navLinkClass(isActive: boolean, collapsed: boolean) {
  return `nav-link ${collapsed ? "justify-center px-0 py-2" : "py-3"} ${isActive ? "nav-link-active" : ""}`;
}

function NavLinkItem({
  item,
  collapsed,
}: {
  item: Extract<WorkspaceNavItem, { type: "link" }>;
  collapsed: boolean;
}) {
  const Icon = getNavIcon(item.icon);
  return (
    <NavLink
      end={item.end}
      to={item.to}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) => navLinkClass(isActive, collapsed)}
    >
      {collapsed ? (
        <div className="w-10 h-10 flex items-center justify-center">
          <Icon className="h-5 w-5" />
        </div>
      ) : (
        <span className="flex items-center">
          <Icon className="h-5 w-5 mr-3" />
          <span>{item.label}</span>
        </span>
      )}
    </NavLink>
  );
}

function NavGroupItem({
  group,
  collapsed,
  pathname,
}: {
  group: WorkspaceNavGroup;
  collapsed: boolean;
  pathname: string;
}) {
  const Icon = getNavIcon(group.icon);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Auto-expand on nested routes; collapse when leaving them (Insurance accordion behavior).
    const shouldOpen = group.openPrefixes.some((prefix) => pathname.startsWith(prefix));
    setOpen(shouldOpen);
  }, [pathname, group.openPrefixes]);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((s) => !s)}
        aria-expanded={open}
        title={collapsed ? group.label : undefined}
        className={`w-full flex items-center ${collapsed ? "justify-center px-0 py-2" : "justify-between px-4 py-3"} rounded-2xl text-sm font-medium transition-all duration-200 ${
          open
            ? "text-slate-800 dark:text-white font-semibold"
            : "text-slate-800 dark:text-white hover:bg-sidebar-accent hover:text-slate-900 dark:hover:text-white"
        }`}
      >
        {!collapsed ? (
          <span className="flex items-center gap-2">
            <svg
              className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
            <span>{group.label}</span>
          </span>
        ) : (
          <div className="w-10 h-10 flex items-center justify-center">
            <Icon className="h-5 w-5" />
          </div>
        )}
      </button>

      <AnimatePresence initial={false}>
        {!collapsed && open ? (
          <motion.div
            key={`${group.id}-submenu`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-1 relative pl-5">
              <div className="absolute left-2 top-2 bottom-2 w-px bg-white/10" aria-hidden />
              {group.children.map((child) => {
                const ChildIcon = getNavIcon(child.icon);
                return (
                  <NavLink
                    key={child.to}
                    end={child.end}
                    to={child.to}
                    className={({ isActive }) =>
                      `block rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 flex items-center ${
                        isActive
                          ? "nav-link-active dark:text-white dark:bg-cyan-500/10 dark:border dark:border-cyan-400/20"
                          : "text-gray-700 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white hover:bg-sidebar-accent/80 dark:hover:bg-white/5"
                      }`
                    }
                  >
                    <span className="flex items-center">
                      <ChildIcon className="h-4 w-4 mr-3 flex-shrink-0 nav-link-icon dark:text-slate-300" />
                      <span>{child.label}</span>
                    </span>
                  </NavLink>
                );
              })}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export function AppSidebar({
  workspace,
  orgName,
  orgSubtitle,
  orgInitials,
  collapsed,
  onToggleCollapsed,
  hasPermission,
  userDisplayName,
  userEmail,
  userInitials,
  onLogout,
}: AppSidebarProps) {
  const location = useLocation();

  const visibleNav = workspace.navigation
    .map((item) => {
      if (item.type === "group") {
        const children = item.children.filter(
          (child) => !child.permission || hasPermission(child.permission)
        );
        if (children.length === 0) return null;
        return { ...item, children };
      }
      if (!item.permission) return item;
      return hasPermission(item.permission) ? item : null;
    })
    .filter((item): item is NonNullable<typeof item> => item != null);

  return (
    <aside
      className={`fixed z-40 ${collapsed ? "left-4 w-[80px]" : "left-4 w-[240px]"} top-14 flex flex-col transition-all duration-300 ease-in-out glass h-[calc(100vh-56px)] overflow-hidden gyantra-sidebar`}
    >
      <div className="px-3 py-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold bg-[#14B8A6] text-[#050816]">
            {orgInitials}
          </div>
          {!collapsed ? (
            <div title={`${orgName}${orgSubtitle ? " — " + orgSubtitle : ""}`}>
              <div className="text-sm font-semibold text-slate-900 dark:text-white">{orgName}</div>
              <div className="text-xs text-gray-700 dark:text-slate-400">{orgSubtitle}</div>
            </div>
          ) : null}
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label="Collapse sidebar"
            className="ml-auto rounded-full border border-border bg-popover px-2 py-1 text-sm hover:bg-popover/80"
          >
            {collapsed ? "›" : "‹"}
          </button>
        </div>
      </div>

      {!collapsed ? (
        <div className="mx-3 mb-2 gyantra-ai-card rounded-xl px-3 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-[#14B8A6] shadow-[0_0_8px_#14B8A6]" />
            <span className="text-xs font-semibold text-[#14B8A6]">{workspace.aiCardTitle}</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-600 dark:text-slate-400">{workspace.aiCardSubtitle}</p>
        </div>
      ) : null}

      <nav className="flex-1 px-2 py-2 flex flex-col gap-1 overflow-y-auto">
        {visibleNav.map((item) =>
          item.type === "group" ? (
            <NavGroupItem key={item.id} group={item} collapsed={collapsed} pathname={location.pathname} />
          ) : (
            <NavLinkItem key={item.to} item={item} collapsed={collapsed} />
          ),
        )}
      </nav>

      <SidebarFooter
        collapsed={collapsed}
        settingsPath={workspace.settingsPath}
        displayName={userDisplayName}
        email={userEmail}
        initials={userInitials}
        onLogout={onLogout}
      />
    </aside>
  );
}
