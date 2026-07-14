import { useMemo, useState } from "react";

import { Button } from "../../components/ui/button";
import {
  ActionMenu,
  KeyIcon,
  PauseIcon,
  PencilIcon,
  PlayIcon,
} from "../../components/ui/ActionMenu";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import {
  useCreatePlatformUser,
  usePlatformOrganizations,
  usePlatformRoles,
  usePlatformUsers,
  useResetPlatformUserPassword,
  useUpdatePlatformUser,
} from "../../lib/platform/hooks";
import { ADMIN_CONSOLE_EYEBROW, formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import { useToast } from "../../components/ui/toast";

export function PlatformUsersPage() {
  const { showToast } = useToast();
  const usersQuery = usePlatformUsers();
  const orgsQuery = usePlatformOrganizations();
  const rolesQuery = usePlatformRoles();
  const createUser = useCreatePlatformUser();
  const updateUser = useUpdatePlatformUser();
  const resetPassword = useResetPlatformUserPassword();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState({ email: "", password: "", organization_id: "", role: "tenant_user" });
  const [newPassword, setNewPassword] = useState("");

  const roles = rolesQuery.data ?? [];
  const organizations = orgsQuery.data ?? [];

  const filtered = useMemo(() => {
    let rows = usersQuery.data ?? [];
    const q = search.trim().toLowerCase();
    if (q) rows = rows.filter((user) => user.email.toLowerCase().includes(q) || (user.organization_name ?? "").toLowerCase().includes(q));
    if (statusFilter === "active") rows = rows.filter((user) => user.is_active);
    if (statusFilter === "inactive") rows = rows.filter((user) => !user.is_active);
    return rows;
  }, [usersQuery.data, search, statusFilter]);

  const selectedUser = (usersQuery.data ?? []).find((user) => user.id === selectedId);

  async function handleCreate() {
    if (!form.email || !form.password || !form.organization_id) return;
    try {
      await createUser.mutateAsync({
        email: form.email,
        password: form.password,
        organization_id: Number(form.organization_id),
        role: form.role,
      });
      setCreateOpen(false);
      setForm({ email: "", password: "", organization_id: "", role: "tenant_user" });
      showToast("User created.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to create user", "error");
    }
  }

  async function handleUpdate() {
    if (!selectedId) return;
    try {
      await updateUser.mutateAsync({
        id: selectedId,
        organization_id: form.organization_id ? Number(form.organization_id) : undefined,
        role: form.role || undefined,
      });
      setEditOpen(false);
      showToast("User updated.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to update user", "error");
    }
  }

  async function handleToggleActive(userId: number, isActive: boolean) {
    try {
      await updateUser.mutateAsync({ id: userId, is_active: !isActive });
      showToast(isActive ? "User deactivated." : "User activated.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to update user status", "error");
    }
  }

  async function handleResetPassword() {
    if (!selectedId || !newPassword) return;
    try {
      await resetPassword.mutateAsync({ id: selectedId, password: newPassword });
      setResetOpen(false);
      setNewPassword("");
      showToast("Password reset successfully.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to reset password", "error");
    }
  }

  if (usersQuery.isLoading) return <LoadingState label="Loading users..." />;

  return (
    <DashboardLayout>
      <SectionCard
        title="Users"
        eyebrow={ADMIN_CONSOLE_EYEBROW}
        action={<Button onClick={() => { setForm({ email: "", password: "", organization_id: organizations[0] ? String(organizations[0].id) : "", role: "tenant_user" }); setCreateOpen(true); }}>Create User</Button>}
      >
        <div className="mb-4 flex flex-col gap-3 md:flex-row">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users..." className="login-input w-full max-w-md px-4 py-2 text-sm" />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)} className="login-input w-full max-w-xs px-4 py-2 text-sm">
            <option value="all">All users</option>
            <option value="active">Active only</option>
            <option value="inactive">Inactive only</option>
          </select>
        </div>

        <PlatformTable
          columns={[
            { key: "email", label: "User" },
            { key: "org", label: "Organization" },
            { key: "role", label: "Role" },
            { key: "status", label: "Status" },
            { key: "actions", label: "", className: "w-14 text-right" },
          ]}
          rows={filtered.map((user) => ({
            id: user.id,
            cells: [
              <div>
                <div className="font-medium">{user.email}</div>
                <div className="text-xs text-slate-500">ID {user.id}</div>
              </div>,
              user.organization_name ?? `Org #${user.organization_id}`,
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium dark:bg-white/10">{formatRoleDisplayLabel(user.role)}</span>,
              <span className={`rounded-full px-2 py-1 text-xs font-medium ${user.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300"}`}>{user.is_active ? "Active" : "Inactive"}</span>,
              <div className="flex justify-end">
                <ActionMenu
                  label={`Actions for ${user.email}`}
                  items={[
                    {
                      id: "edit",
                      label: "Edit",
                      icon: <PencilIcon />,
                      onSelect: () => {
                        setSelectedId(user.id);
                        setForm({
                          email: user.email,
                          password: "",
                          organization_id: String(user.organization_id),
                          role: user.role,
                        });
                        setEditOpen(true);
                      },
                    },
                    {
                      id: "reset-password",
                      label: "Reset Password",
                      icon: <KeyIcon />,
                      onSelect: () => {
                        setSelectedId(user.id);
                        setResetOpen(true);
                      },
                    },
                    user.is_active
                      ? {
                          id: "deactivate",
                          label: "Deactivate",
                          icon: <PauseIcon />,
                          tone: "warning" as const,
                          onSelect: () => {
                            void handleToggleActive(user.id, user.is_active);
                          },
                        }
                      : {
                          id: "activate",
                          label: "Activate",
                          icon: <PlayIcon />,
                          onSelect: () => {
                            void handleToggleActive(user.id, user.is_active);
                          },
                        },
                  ]}
                />
              </div>,
            ],
          }))}
        />
      </SectionCard>

      <PlatformDialog open={createOpen} title="Create User" onClose={() => setCreateOpen(false)} size="lg" footer={<><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button onClick={() => void handleCreate()} disabled={createUser.isPending}>Create User</Button></>}>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block sm:col-span-2"><span className="text-sm font-medium">Email</span><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} type="email" className="login-input mt-2 w-full px-4 py-2 text-sm" /></label>
          <label className="block sm:col-span-2"><span className="text-sm font-medium">Password</span><input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} type="password" className="login-input mt-2 w-full px-4 py-2 text-sm" /></label>
          <label className="block"><span className="text-sm font-medium">Organization</span><select value={form.organization_id} onChange={(e) => setForm({ ...form, organization_id: e.target.value })} className="login-input mt-2 w-full px-4 py-2 text-sm">{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
          <label className="block"><span className="text-sm font-medium">Role</span><select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="login-input mt-2 w-full px-4 py-2 text-sm">{roles.map((role) => <option key={role.id} value={role.name}>{formatRoleDisplayLabel(role.name)}</option>)}</select></label>
        </div>
      </PlatformDialog>

      <PlatformDialog open={editOpen} title="Edit User" description={selectedUser?.email} onClose={() => setEditOpen(false)} footer={<><Button variant="outline" onClick={() => setEditOpen(false)}>Cancel</Button><Button onClick={() => void handleUpdate()} disabled={updateUser.isPending}>Save Changes</Button></>}>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block"><span className="text-sm font-medium">Organization</span><select value={form.organization_id} onChange={(e) => setForm({ ...form, organization_id: e.target.value })} className="login-input mt-2 w-full px-4 py-2 text-sm">{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
          <label className="block"><span className="text-sm font-medium">Role</span><select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="login-input mt-2 w-full px-4 py-2 text-sm">{roles.map((role) => <option key={role.id} value={role.name}>{formatRoleDisplayLabel(role.name)}</option>)}</select></label>
        </div>
      </PlatformDialog>

      <PlatformDialog open={resetOpen} title="Reset Password" description={selectedUser?.email} onClose={() => setResetOpen(false)} footer={<><Button variant="outline" onClick={() => setResetOpen(false)}>Cancel</Button><Button onClick={() => void handleResetPassword()} disabled={resetPassword.isPending}>Reset Password</Button></>}>
        <label className="block"><span className="text-sm font-medium">New password</span><input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} type="password" className="login-input mt-2 w-full px-4 py-2 text-sm" /></label>
      </PlatformDialog>
    </DashboardLayout>
  );
}
