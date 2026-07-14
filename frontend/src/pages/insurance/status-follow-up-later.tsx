import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListFollowups } from "../../lib/api/hooks";
import { FollowUpCard } from "../../components/insurance/FollowUpCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function FollowUpLaterPage() {
  const { organizationId } = useWorkbench();
  const q = useListFollowups(organizationId, "follow_up_later");

  if (q.isLoading) return <Loading label="Loading follow-up later..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No follow-up-later leads" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Follow-up Later</h2>
      <div className="mt-4 space-y-3">{q.data.map((f: any) => <FollowUpCard key={f.id} item={f} />)}</div>
    </div>
  );
}

export default FollowUpLaterPage;
