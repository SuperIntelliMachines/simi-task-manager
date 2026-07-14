import { useMemo, useState } from "react";

import { Button } from "../../components/ui/button";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import { useCreatePlatformRole, usePlatformPermissions, usePlatformRoles, useUpdateRolePermissions } from "../../lib/platform/hooks";
import { ADMIN_CONSOLE_EYEBROW, formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import {
  formatPermissionActionLabel,
  groupPermissionsByModule,
} from "../../lib/auth/permission-labels";
import { useToast } from "../../components/ui/toast";

export function PlatformRolesPage() {
  const { showToast } = useToast();
  const rolesQuery = usePlatformRoles();
  const permissionsQuery = usePlatformPermissions();
  const createRole = useCreatePlatformRole();
  const updatePermissions = useUpdateRolePermissions();

  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleDescription, setRoleDescription] = useState("");
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  const permissions = permissionsQuery.data ?? [];
  const permissionGroups = useMemo(() => groupPermissionsByModule(permissions), [permissions]);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (rolesQuery.data ?? []).filter((role) => role.name.includes(q) || (role.description ?? "").toLowerCase().includes(q) || formatRoleDisplayLabel(role.name).toLowerCase().includes(q));
  }, [rolesQuery.data, search]);

  const selectedRole = (rolesQuery.data ?? []).find((role) => role.id === selectedRoleId);

  async function handleCreateRole() {
    if (!roleName.trim()) return;
    try {
      await createRole.mutateAsync({ name: roleName.trim(), description: roleDescription || undefined });
      setCreateOpen(false);
      setRoleName("");
      setRoleDescription("");
      showToast("Role created.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to create role", "error");
    }
  }

  async function handleSavePermissions() {
    if (!selectedRoleId) return;
    try {
      await updatePermissions.mutateAsync({ roleId: selectedRoleId, codes: selectedPermissions });
      setPermissionsOpen(false);
      showToast("Role permissions updated.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to update permissions", "error");
    }
  }

  function togglePermission(code: string) {
    setSelectedPermissions((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  if (rolesQuery.isLoading) return <LoadingState label="Loading roles..." />;

  return (
    <DashboardLayout>
      <SectionCard title="Roles" eyebrow={ADMIN_CONSOLE_EYEBROW} action={<Button onClick={() => setCreateOpen(true)}>Create Role</Button>}>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search roles..." className="login-input mb-4 w-full max-w-md px-4 py-2 text-sm" />
        <PlatformTable
          columns={[
            { key: "name", label: "Role" },
            { key: "type", label: "Type" },
            { key: "permissions", label: "Permissions" },
            { key: "actions", label: "Actions", className: "text-right" },
          ]}
          rows={filtered.map((role) => ({
            id: role.id,
            cells: [
              <div>
                <div className="font-medium">{formatRoleDisplayLabel(role.name)}</div>
                <div className="text-xs text-slate-500">{role.description || "No description"}</div>
              </div>,
              role.is_system ? "System" : "Custom",
              <span className="text-sm text-slate-600 dark:text-slate-300">{role.permissions.length} assigned</span>,
              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={role.is_system}
                  className="text-sm font-medium text-[#14B8A6] hover:underline disabled:cursor-not-allowed disabled:text-slate-400"
                  onClick={() => {
                    setSelectedRoleId(role.id);
                    setSelectedPermissions(role.permissions);
                    setPermissionsOpen(true);
                  }}
                >
                  Edit Permissions
                </button>
              </div>,
            ],
          }))}
        />
      </SectionCard>

      <PlatformDialog open={createOpen} title="Create Role" onClose={() => setCreateOpen(false)} footer={<><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button onClick={() => void handleCreateRole()} disabled={createRole.isPending}>Create</Button></>}>
        <label className="block"><span className="text-sm font-medium">Role name</span><input value={roleName} onChange={(e) => setRoleName(e.target.value)} className="login-input mt-2 w-full px-4 py-2 text-sm" /></label>
        <label className="mt-4 block"><span className="text-sm font-medium">Description</span><textarea value={roleDescription} onChange={(e) => setRoleDescription(e.target.value)} className="login-input mt-2 w-full px-4 py-2 text-sm" rows={3} /></label>
      </PlatformDialog>

      <PlatformDialog open={permissionsOpen} title="Edit Permissions" description={selectedRole ? formatRoleDisplayLabel(selectedRole.name) : undefined} onClose={() => setPermissionsOpen(false)} size="xl" footer={<><Button variant="outline" onClick={() => setPermissionsOpen(false)}>Cancel</Button><Button onClick={() => void handleSavePermissions()} disabled={updatePermissions.isPending}>Save Permissions</Button></>}>
        <div className="max-h-[50vh] space-y-4 overflow-y-auto rounded-2xl border border-slate-200/80 p-4 dark:border-white/10">
          {permissionGroups.map((group) => (
            <div key={group.moduleKey}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#14B8A6]">{group.moduleLabel}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {group.permissions.map((permission) => (
                  <label
                    key={permission.id}
                    className="flex items-start gap-3 rounded-xl border border-transparent px-3 py-2 hover:border-[#14B8A6]/20 hover:bg-white/40 dark:hover:bg-white/5"
                  >
                    <input
                      type="checkbox"
                      checked={selectedPermissions.includes(permission.code)}
                      onChange={() => togglePermission(permission.code)}
                      className="mt-1"
                    />
                    <span>
                      <span className="block text-sm font-medium">
                        {formatPermissionActionLabel(permission.permission || permission.code)}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {permission.description || group.moduleLabel}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </PlatformDialog>
    </DashboardLayout>
  );
}
