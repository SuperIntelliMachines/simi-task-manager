import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies } from "../../lib/api/hooks";
import { PolicyCard } from "../../components/insurance/PolicyCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function EscalatedRenewalsPage() {
  const { organizationId } = useWorkbench();
  const q = useListPolicies(organizationId, "escalated");

  if (q.isLoading) return <Loading label="Loading escalated renewals..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No escalated renewals" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Escalated Renewals</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{q.data.map((p) => <PolicyCard key={p.id} item={p} />)}</div>
    </div>
  );
}

export default EscalatedRenewalsPage;
