import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies } from "../../lib/api/hooks";
import { PolicyCard } from "../../components/insurance/PolicyCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function AssignedPoliciesPage() {
  const { organizationId } = useWorkbench();
  const q = useListPolicies(organizationId);

  if (q.isLoading) return <Loading label="Loading assigned policies..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No assigned policies" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Assigned Policies</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{q.data.map((p) => <PolicyCard key={p.id} item={p} />)}</div>
    </div>
  );
}

export default AssignedPoliciesPage;
