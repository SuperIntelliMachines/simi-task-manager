import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import {
  ActionMenu,
  EyeIcon,
  PencilIcon,
  TrashIcon,
} from "../../components/ui/ActionMenu";
import { ADMIN_CONSOLE_EYEBROW } from "../../lib/auth/role-labels";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import {
  OrganizationDeleteBlockedError,
  type OrganizationDeleteDependency,
} from "../../lib/platform/api";
import {
  useCreateOrganization,
  useDeleteOrganization,
  usePlatformOrganizations,
  useUpdateOrganization,
} from "../../lib/platform/hooks";
import { useToast } from "../../components/ui/toast";

export function PlatformOrganizationsPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const orgsQuery = usePlatformOrganizations();
  const createOrg = useCreateOrganization();
  const updateOrg = useUpdateOrganization();
  const deleteOrg = useDeleteOrganization();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "recent">("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [blockedOpen, setBlockedOpen] = useState(false);
  const [blockedDependencies, setBlockedDependencies] = useState<OrganizationDeleteDependency[]>([]);
  const [nameInput, setNameInput] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    let rows = orgsQuery.data ?? [];
    const q = search.trim().toLowerCase();
    if (q) rows = rows.filter((org) => org.name.toLowerCase().includes(q));
    if (statusFilter === "recent") {
      rows = [...rows].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))).slice(0, 20);
    }
    return rows;
  }, [orgsQuery.data, search, statusFilter]);

  const selectedOrg = filtered.find((org) => org.id === selectedId) ?? (orgsQuery.data ?? []).find((org) => org.id === selectedId);

  async function handleCreate() {
    if (!nameInput.trim()) return;
    try {
      await createOrg.mutateAsync({ name: nameInput.trim() });
      setCreateOpen(false);
      setNameInput("");
      showToast("Organization created.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to create organization", "error");
    }
  }

  async function handleUpdate() {
    if (!selectedId || !nameInput.trim()) return;
    try {
      await updateOrg.mutateAsync({ id: selectedId, name: nameInput.trim() });
      setEditOpen(false);
      showToast("Organization updated.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to update organization", "error");
    }
  }

  async function handleDelete() {
    if (!selectedId) return;
    try {
      await deleteOrg.mutateAsync(selectedId);
      setDeleteOpen(false);
      setSelectedId(null);
      showToast("Organization deleted.", "success");
    } catch (error) {
      if (error instanceof OrganizationDeleteBlockedError) {
        setDeleteOpen(false);
        setBlockedDependencies(error.dependencies);
        setBlockedOpen(true);
        return;
      }
      showToast(error instanceof Error ? error.message : "Failed to delete organization", "error");
    }
  }

  if (orgsQuery.isLoading) return <LoadingState label="Loading organizations..." />;

  return (
    <DashboardLayout>
      <SectionCard
        title="Organizations"
        eyebrow={ADMIN_CONSOLE_EYEBROW}
        action={
          <Button onClick={() => { setNameInput(""); setCreateOpen(true); }}>Create Organization</Button>
        }
      >
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search organizations..."
            className="login-input w-full max-w-md px-4 py-2 text-sm text-slate-900 dark:text-white"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "all" | "recent")}
            className="login-input w-full max-w-xs px-4 py-2 text-sm text-slate-900 dark:text-white"
          >
            <option value="all">All organizations</option>
            <option value="recent">Recently created</option>
          </select>
        </div>

        <PlatformTable
          columns={[
            { key: "name", label: "Organization" },
            { key: "created", label: "Created" },
            { key: "actions", label: "", className: "w-14 text-right" },
          ]}
          rows={filtered.map((org) => ({
            id: org.id,
            cells: [
              <div>
                <div className="font-medium text-slate-900 dark:text-white">{org.name}</div>
                <div className="text-xs text-slate-500">ID {org.id}</div>
              </div>,
              org.created_at ? new Date(org.created_at).toLocaleString() : "—",
              <div className="flex justify-end">
                <ActionMenu
                  label={`Actions for ${org.name}`}
                  items={[
                    {
                      id: "view",
                      label: "View Organization",
                      icon: <EyeIcon />,
                      onSelect: () => {
                        navigate(`/master/organizations/${org.id}`);
                      },
                    },
                    {
                      id: "edit",
                      label: "Edit Organization",
                      icon: <PencilIcon />,
                      onSelect: () => {
                        setSelectedId(org.id);
                        setNameInput(org.name);
                        setEditOpen(true);
                      },
                    },
                    {
                      id: "delete",
                      label: "Delete Organization",
                      icon: <TrashIcon />,
                      tone: "danger",
                      onSelect: () => {
                        setSelectedId(org.id);
                        setDeleteOpen(true);
                      },
                    },
                  ]}
                />
              </div>,
            ],
          }))}
        />
      </SectionCard>

      <PlatformDialog open={createOpen} title="Create Organization" onClose={() => setCreateOpen(false)} footer={<><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button onClick={() => void handleCreate()} disabled={createOrg.isPending}>Create</Button></>}>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Organization name</label>
        <input value={nameInput} onChange={(e) => setNameInput(e.target.value)} className="login-input mt-2 w-full px-4 py-2 text-sm" />
      </PlatformDialog>

      <PlatformDialog open={editOpen} title="Edit Organization" onClose={() => setEditOpen(false)} footer={<><Button variant="outline" onClick={() => setEditOpen(false)}>Cancel</Button><Button onClick={() => void handleUpdate()} disabled={updateOrg.isPending}>Save</Button></>}>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Organization name</label>
        <input value={nameInput} onChange={(e) => setNameInput(e.target.value)} className="login-input mt-2 w-full px-4 py-2 text-sm" />
      </PlatformDialog>

      <PlatformDialog
        open={deleteOpen}
        title="Delete Organization"
        description={selectedOrg ? `Delete ${selectedOrg.name}? This only works when the organization has no users or other related business data.` : undefined}
        onClose={() => setDeleteOpen(false)}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button onClick={() => void handleDelete()} disabled={deleteOrg.isPending}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Organizations with users or related business data cannot be deleted until those items are removed or reassigned.
        </p>
      </PlatformDialog>

      <PlatformDialog
        open={blockedOpen}
        title="Cannot Delete Organization"
        onClose={() => setBlockedOpen(false)}
        footer={<Button onClick={() => setBlockedOpen(false)}>Close</Button>}
      >
        <div className="space-y-4 text-sm text-slate-700 dark:text-slate-300">
          <p>This organization still contains business data.</p>
          <p>Before deleting it, remove or reassign the following:</p>
          <ul className="list-disc space-y-1 pl-5">
            {blockedDependencies.map((item) => (
              <li key={item.label}>
                {item.label} ({item.count})
              </li>
            ))}
          </ul>
          <p className="text-slate-500 dark:text-slate-400">
            You may archive the organization instead if you want to preserve historical records.
          </p>
        </div>
      </PlatformDialog>
    </DashboardLayout>
  );
}
