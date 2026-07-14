import { useWorkbench } from "../../app/providers/workbench-provider";
import { DashboardLayout, SectionCard } from "../../components/design-system";
import { Button } from "../../components/ui/button";
import { formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import { CLAIMS_WORKSPACE_NAME } from "../../lib/claims/navigation";

export function ClaimsSettingsPage() {
  const { currentUser, apiRole, organizationName, signOut } = useWorkbench();

  async function handleLogout() {
    await signOut();
  }

  return (
    <DashboardLayout>
      <SectionCard title="Settings" eyebrow={CLAIMS_WORKSPACE_NAME}>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{currentUser?.email || "—"}</dd>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Role</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{formatRoleDisplayLabel(apiRole)}</dd>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40 sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Organization</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{organizationName || CLAIMS_WORKSPACE_NAME}</dd>
          </div>
        </dl>
        <Button className="mt-6" variant="outline" onClick={() => void handleLogout()}>
          Sign out
        </Button>
      </SectionCard>
    </DashboardLayout>
  );
}
