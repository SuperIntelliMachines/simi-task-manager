import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListFollowups } from "../../lib/api/hooks";
import { FollowUpCard } from "../../components/insurance/FollowUpCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function PendingActionsPage() {
  const { organizationId } = useWorkbench();
  const q = useListFollowups(organizationId, "pending_actions");

  if (q.isLoading) return <Loading label="Loading pending actions..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No pending actions" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Pending Actions</h2>
      <div className="mt-4 space-y-3">{q.data.map((f: any) => <FollowUpCard key={f.id} item={f} />)}</div>
    </div>
  );
}

export default PendingActionsPage;
