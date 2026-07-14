import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListFollowups } from "../../lib/api/hooks";
import { FollowUpCard } from "../../components/insurance/FollowUpCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";
import { filterFollowupsByDue, type FollowupDueFilter } from "../../lib/utils/followup-due-filter";
import {
  FOLLOWUP_DUE_FILTER_LABELS,
  parseFollowupDueFilter,
} from "../../lib/insurance/followup-list-navigation";

function parseDueFilter(value: string | null): FollowupDueFilter | undefined {
  return parseFollowupDueFilter(value) ?? undefined;
}

export function FollowupTrackingPage() {
  const { organizationId } = useWorkbench();
  const [searchParams] = useSearchParams();
  const status = searchParams.get("status") || undefined;
  const dueFilter = parseDueFilter(searchParams.get("due"));

  const fetchAll = status === "follow_up_pending" || dueFilter != null;
  const q = useListFollowups(organizationId, fetchAll ? undefined : status);

  const displayed = useMemo(() => {
    if (!q.data) return [];
    let records = q.data;
    if (status === "follow_up_pending") {
      records = records.filter((f: { status: string }) => f.status === "follow_up_pending");
    }
    if (dueFilter) {
      records = filterFollowupsByDue(records, dueFilter);
    }
    return records;
  }, [q.data, status, dueFilter]);

  if (organizationId == null) return <Loading label="Loading organization..." />;
  if (q.isLoading) return <Loading label="Loading follow-ups..." />;

  const pageHeader = (
    <header>
      <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Lead Follow-up</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400 md:text-base">
        {dueFilter
          ? `Showing ${FOLLOWUP_DUE_FILTER_LABELS[dueFilter].toLowerCase()}`
          : "Manage incoming lead follow-ups and update their statuses"}
      </p>
      {dueFilter ? (
        <span className="mt-3 inline-flex rounded-full border border-[#14B8A6]/30 bg-[#14B8A6]/10 px-3 py-1 text-xs font-semibold text-[#14B8A6]">
          {FOLLOWUP_DUE_FILTER_LABELS[dueFilter]}
        </span>
      ) : null}
    </header>
  );

  if (!q.data || displayed.length === 0) {
    const emptyMessage = dueFilter
      ? `No ${FOLLOWUP_DUE_FILTER_LABELS[dueFilter].toLowerCase()}`
      : "No follow-ups";
    return (
      <div className="relative pb-10">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-64 overflow-hidden" aria-hidden>
          <div className="absolute -right-16 top-0 h-56 w-56 rounded-full bg-[#8B5CF6]/10 blur-3xl" />
          <div className="absolute left-1/4 top-8 h-40 w-40 rounded-full bg-[#14B8A6]/10 blur-3xl" />
        </div>
        <div className="relative mx-auto max-w-[820px] space-y-5 px-1">
          {pageHeader}
          <EmptyState message={emptyMessage} />
        </div>
      </div>
    );
  }

  return (
    <div className="relative pb-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-56 w-56 rounded-full bg-[#8B5CF6]/10 blur-3xl" />
        <div className="absolute left-1/4 top-8 h-40 w-40 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-[820px] space-y-5 px-1">
        {pageHeader}

        <div className="space-y-4">
          {displayed.map((f: { id: number }, index: number) => (
            <FollowUpCard key={f.id} item={f} index={index} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default FollowupTrackingPage;
