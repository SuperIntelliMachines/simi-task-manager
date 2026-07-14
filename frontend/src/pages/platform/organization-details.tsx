import { Link, useParams } from "react-router-dom";

import { ADMIN_CONSOLE_EYEBROW } from "../../lib/auth/role-labels";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { usePlatformOrganization } from "../../lib/platform/hooks";
import { Button } from "../../components/ui/button";

export function PlatformOrganizationDetailsPage() {
  const { organizationId } = useParams();
  const id = organizationId ? Number(organizationId) : null;
  const orgQuery = usePlatformOrganization(id);

  if (orgQuery.isLoading) return <LoadingState label="Loading organization..." />;
  if (!orgQuery.data) {
    return (
      <DashboardLayout>
        <SectionCard title="Organization not found" eyebrow={ADMIN_CONSOLE_EYEBROW}>
          <Button asChild variant="outline"><Link to="/master/organizations">Back to organizations</Link></Button>
        </SectionCard>
      </DashboardLayout>
    );
  }

  const org = orgQuery.data;

  return (
    <DashboardLayout>
      <SectionCard
        title={org.name}
        eyebrow={ADMIN_CONSOLE_EYEBROW}
        action={<Button asChild variant="outline"><Link to="/master/organizations">Back</Link></Button>}
      >
        <dl className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Organization ID</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{org.id}</dd>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Created</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{org.created_at ? new Date(org.created_at).toLocaleString() : "—"}</dd>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white/50 p-4 dark:border-white/10 dark:bg-slate-950/40">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Updated</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{org.updated_at ? new Date(org.updated_at).toLocaleString() : "—"}</dd>
          </div>
        </dl>
      </SectionCard>
    </DashboardLayout>
  );
}
