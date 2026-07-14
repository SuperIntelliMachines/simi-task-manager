import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { ADMIN_CONSOLE_EYEBROW, formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import {
  formatPermissionActionLabel,
  formatPermissionModuleLabel,
  groupPermissionsByModule,
  parsePermissionCode,
} from "../../lib/auth/permission-labels";
import { usePlatformPermissions, usePlatformRoles } from "../../lib/platform/hooks";
import type { PlatformPermission, PlatformRole } from "../../lib/platform/types";

type ViewMode = "details" | "matrix";

function permissionMatchesQuery(permission: PlatformPermission, query: string): boolean {
  if (!query) return true;
  const display = formatPermissionModuleLabel(permission.module) + " " + formatPermissionActionLabel(permission.permission || permission.code);
  return (
    permission.code.toLowerCase().includes(query) ||
    (permission.description ?? "").toLowerCase().includes(query) ||
    permission.module.toLowerCase().includes(query) ||
    (permission.permission ?? "").toLowerCase().includes(query) ||
    display.toLowerCase().includes(query)
  );
}

function roleMatchesQuery(role: PlatformRole, query: string): boolean {
  if (!query) return true;
  const label = formatRoleDisplayLabel(role.name).toLowerCase();
  return role.name.toLowerCase().includes(query) || label.includes(query) || (role.description ?? "").toLowerCase().includes(query);
}

export function PlatformPermissionsPage() {
  const permissionsQuery = usePlatformPermissions();
  const rolesQuery = usePlatformRoles();

  const [view, setView] = useState<ViewMode>("details");
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>({});

  const permissions = permissionsQuery.data ?? [];
  const roles = rolesQuery.data ?? [];

  const modules = useMemo(() => {
    const keys = Array.from(
      new Set(permissions.map((p) => (p.module || parsePermissionCode(p.code).module).toLowerCase())),
    ).sort((a, b) => formatPermissionModuleLabel(a).localeCompare(formatPermissionModuleLabel(b)));
    return keys;
  }, [permissions]);

  const query = search.trim().toLowerCase();

  const filteredRoles = useMemo(() => {
    let list = roles;
    if (roleFilter !== "all") {
      list = list.filter((role) => String(role.id) === roleFilter);
    }
    if (query) {
      list = list.filter(
        (role) =>
          roleMatchesQuery(role, query) ||
          role.permissions.some((code) => {
            const perm = permissions.find((p) => p.code === code);
            return perm ? permissionMatchesQuery(perm, query) : code.toLowerCase().includes(query);
          }),
      );
    }
    return list;
  }, [roles, roleFilter, query, permissions]);

  const filteredPermissions = useMemo(() => {
    let rows = permissions;
    if (moduleFilter !== "all") {
      rows = rows.filter((p) => (p.module || parsePermissionCode(p.code).module).toLowerCase() === moduleFilter);
    }
    if (query) {
      rows = rows.filter((p) => permissionMatchesQuery(p, query));
    }
    return rows;
  }, [permissions, moduleFilter, query]);

  useEffect(() => {
    if (selectedRoleId != null && filteredRoles.some((role) => role.id === selectedRoleId)) return;
    setSelectedRoleId(filteredRoles[0]?.id ?? null);
  }, [filteredRoles, selectedRoleId]);

  const selectedRole = roles.find((role) => role.id === selectedRoleId) ?? null;

  const detailsGroups = useMemo(() => {
    if (!selectedRole) return [];
    const assigned = new Set(selectedRole.permissions);
    const roleMatched = Boolean(query && roleMatchesQuery(selectedRole, query));

    let rows = permissions.filter((p) => assigned.has(p.code));
    if (moduleFilter !== "all") {
      rows = rows.filter(
        (p) => (p.module || parsePermissionCode(p.code).module).toLowerCase() === moduleFilter,
      );
    }
    if (query && !roleMatched) {
      rows = rows.filter((p) => permissionMatchesQuery(p, query));
    }
    return groupPermissionsByModule(rows);
  }, [selectedRole, permissions, moduleFilter, query]);

  const matrixGroups = useMemo(() => groupPermissionsByModule(filteredPermissions), [filteredPermissions]);

  const matrixRoles = useMemo(() => {
    if (roleFilter === "all") return roles;
    return roles.filter((role) => String(role.id) === roleFilter);
  }, [roles, roleFilter]);

  function isModuleExpanded(moduleKey: string): boolean {
    if (expandedModules[moduleKey] !== undefined) return expandedModules[moduleKey];
    return true; // default expanded
  }

  function toggleModule(moduleKey: string) {
    setExpandedModules((current) => ({
      ...current,
      [moduleKey]: !isModuleExpanded(moduleKey),
    }));
  }

  if (permissionsQuery.isLoading || rolesQuery.isLoading) {
    return <LoadingState label="Loading permissions..." />;
  }

  return (
    <DashboardLayout>
      <SectionCard
        title="Permissions"
        eyebrow={ADMIN_CONSOLE_EYEBROW}
        action={
          <div className="inline-flex rounded-full border border-slate-200/80 bg-white/60 p-1 dark:border-white/10 dark:bg-slate-950/60">
            {(
              [
                { id: "details" as const, label: "Role Details" },
                { id: "matrix" as const, label: "Permission Matrix" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setView(tab.id)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  view === tab.id
                    ? "bg-[#14B8A6] text-[#050816] shadow-sm"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        }
      >
        <div className="mb-5 flex flex-col gap-3 lg:flex-row">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by module, permission, or role..."
            className="login-input w-full flex-1 px-4 py-2.5 text-sm"
            aria-label="Search permissions"
          />
          <select
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
            className="login-input w-full max-w-xs px-4 py-2.5 text-sm"
            aria-label="Filter by module"
          >
            <option value="all">All modules</option>
            {modules.map((moduleKey) => (
              <option key={moduleKey} value={moduleKey}>
                {formatPermissionModuleLabel(moduleKey)}
              </option>
            ))}
          </select>
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              if (e.target.value !== "all") setSelectedRoleId(Number(e.target.value));
            }}
            className="login-input w-full max-w-xs px-4 py-2.5 text-sm"
            aria-label="Filter by role"
          >
            <option value="all">All roles</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {formatRoleDisplayLabel(role.name)}
              </option>
            ))}
          </select>
        </div>

        {view === "details" ? (
          <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
            <aside className="rounded-2xl border border-slate-200/80 bg-white/55 p-3 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70">
              <div className="mb-3 px-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#14B8A6]">Roles</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {filteredRoles.length} role{filteredRoles.length === 1 ? "" : "s"}
                </p>
              </div>
              <div className="flex max-h-[min(70vh,640px)] flex-col gap-1 overflow-y-auto">
                {filteredRoles.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-slate-500">No roles match your filters.</p>
                ) : (
                  filteredRoles.map((role) => {
                    const active = role.id === selectedRoleId;
                    const assignedCount = role.permissions.filter((code) =>
                      filteredPermissions.some((p) => p.code === code),
                    ).length;
                    return (
                      <button
                        key={role.id}
                        type="button"
                        onClick={() => setSelectedRoleId(role.id)}
                        className={`rounded-xl px-3 py-3 text-left transition ${
                          active
                            ? "border border-[#14B8A6]/35 bg-[#14B8A6]/10 shadow-sm dark:bg-[#14B8A6]/15"
                            : "border border-transparent hover:bg-slate-50/80 dark:hover:bg-white/5"
                        }`}
                      >
                        <div className="text-sm font-semibold text-slate-900 dark:text-white">
                          {formatRoleDisplayLabel(role.name)}
                        </div>
                        <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                          {assignedCount} permission{assignedCount === 1 ? "" : "s"}
                          {role.is_system ? " · System" : ""}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </aside>

            <div className="rounded-2xl border border-slate-200/80 bg-white/55 p-4 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70 sm:p-5">
              {!selectedRole ? (
                <p className="py-16 text-center text-sm text-slate-500">Select a role to view its permissions.</p>
              ) : (
                <>
                  <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-slate-200/70 pb-4 dark:border-white/10">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#14B8A6]">
                        Permissions for
                      </p>
                      <h3 className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">
                        {formatRoleDisplayLabel(selectedRole.name)}
                      </h3>
                      {selectedRole.description ? (
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{selectedRole.description}</p>
                      ) : null}
                    </div>
                    <div className="rounded-full border border-slate-200/80 bg-white/70 px-3 py-1 text-xs font-medium text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                      {selectedRole.permissions.length} total assigned
                    </div>
                  </div>

                  {detailsGroups.length === 0 ? (
                    <p className="py-12 text-center text-sm text-slate-500">
                      No permissions match the current filters for this role.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {detailsGroups.map((group) => {
                        const open = isModuleExpanded(group.moduleKey);
                        return (
                          <div
                            key={group.moduleKey}
                            className="overflow-hidden rounded-2xl border border-slate-200/70 dark:border-white/10"
                          >
                            <button
                              type="button"
                              onClick={() => toggleModule(group.moduleKey)}
                              className="flex w-full items-center justify-between gap-3 bg-slate-50/80 px-4 py-3 text-left dark:bg-white/5"
                              aria-expanded={open}
                            >
                              <span className="flex items-center gap-2">
                                <svg
                                  className={`h-3.5 w-3.5 text-slate-500 transition-transform ${open ? "rotate-90" : ""}`}
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth={2}
                                  aria-hidden
                                >
                                  <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                <span className="text-sm font-semibold text-slate-900 dark:text-white">
                                  {group.moduleLabel}
                                </span>
                              </span>
                              <span className="text-xs text-slate-500 dark:text-slate-400">
                                {group.permissions.length} granted
                              </span>
                            </button>

                            <AnimatePresence initial={false}>
                              {open ? (
                                <motion.div
                                  key={`${group.moduleKey}-body`}
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: "auto", opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                                  className="overflow-hidden"
                                >
                                  <ul className="grid gap-1 px-3 py-3 sm:grid-cols-2 xl:grid-cols-3">
                                    {group.permissions.map((permission) => (
                                      <li
                                        key={permission.id}
                                        className="flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-slate-800 dark:text-slate-100"
                                      >
                                        <span
                                          className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300"
                                          aria-hidden
                                        >
                                          ✓
                                        </span>
                                        <span className="font-medium">
                                          {formatPermissionActionLabel(permission.permission || permission.code)}
                                        </span>
                                      </li>
                                    ))}
                                  </ul>
                                </motion.div>
                              ) : null}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200/80 bg-white/55 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200/80 bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
                <tr>
                  <th className="sticky left-0 z-10 bg-slate-50/95 px-4 py-3 dark:bg-slate-950/95">Permission</th>
                  {matrixRoles.map((role) => (
                    <th key={role.id} className="px-4 py-3 whitespace-nowrap">
                      {formatRoleDisplayLabel(role.name)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixGroups.length === 0 ? (
                  <tr>
                    <td colSpan={matrixRoles.length + 1} className="px-4 py-12 text-center text-slate-500">
                      No permissions match your filters.
                    </td>
                  </tr>
                ) : (
                  matrixGroups.map((group) => (
                    <ModuleMatrixRows
                      key={group.moduleKey}
                      moduleLabel={group.moduleLabel}
                      permissions={group.permissions}
                      roles={matrixRoles}
                      colSpan={matrixRoles.length + 1}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </DashboardLayout>
  );
}

function ModuleMatrixRows({
  moduleLabel,
  permissions,
  roles,
  colSpan,
}: {
  moduleLabel: string;
  permissions: PlatformPermission[];
  roles: PlatformRole[];
  colSpan: number;
}) {
  return (
    <>
      <tr className="bg-slate-100/80 dark:bg-white/[0.04]">
        <td colSpan={colSpan} className="px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.16em] text-[#14B8A6]">
          {moduleLabel}
        </td>
      </tr>
      {permissions.map((permission) => (
        <tr key={permission.id} className="border-t border-slate-200/60 hover:bg-slate-50/80 dark:border-white/5 dark:hover:bg-white/5">
          <td className="sticky left-0 z-10 bg-white/95 px-4 py-3 dark:bg-slate-950/95">
            <div className="font-medium text-slate-900 dark:text-white">
              {formatPermissionActionLabel(permission.permission || permission.code)}
            </div>
            {permission.description ? (
              <div className="text-xs text-slate-500">{permission.description}</div>
            ) : null}
          </td>
          {roles.map((role) => (
            <td key={`${permission.id}-${role.id}`} className="px-4 py-3 text-center">
              {role.permissions.includes(permission.code) ? (
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
                  ✓
                </span>
              ) : (
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-white/5">
                  —
                </span>
              )}
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
