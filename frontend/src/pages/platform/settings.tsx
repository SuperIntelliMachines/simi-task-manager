import { ADMIN_CONSOLE_EYEBROW, ADMIN_CONSOLE_NAME, formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import { DashboardLayout, SectionCard } from "../../components/design-system";
import { Button } from "../../components/ui/button";
import { useWorkbench } from "../../app/providers/workbench-provider";

export function PlatformSettingsPage() {
  const { currentUser, apiRole, organizationName, signOut } = useWorkbench();

  return (
    <DashboardLayout>
      <SectionCard title={`${ADMIN_CONSOLE_NAME} Settings`} eyebrow={ADMIN_CONSOLE_EYEBROW}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-5 dark:border-white/10 dark:bg-slate-950/40">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#14B8A6]">Administrator Profile</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <div><dt className="text-slate-500">Email</dt><dd className="font-medium text-slate-900 dark:text-white">{currentUser?.email || "—"}</dd></div>
              <div><dt className="text-slate-500">Role</dt><dd className="font-medium text-slate-900 dark:text-white">{formatRoleDisplayLabel(apiRole)}</dd></div>
              <div><dt className="text-slate-500">Home Organization</dt><dd className="font-medium text-slate-900 dark:text-white">{organizationName || "—"}</dd></div>
            </dl>
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-5 dark:border-white/10 dark:bg-slate-950/40">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#14B8A6]">Session</h3>
            <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
              The {ADMIN_CONSOLE_NAME.toLowerCase()} uses the same SIMI authentication session and RBAC permissions as the organization workspace.
            </p>
            <Button className="mt-5" variant="outline" onClick={() => void signOut()}>Sign out of SIMI</Button>
          </div>
        </div>
      </SectionCard>
    </DashboardLayout>
  );
}
