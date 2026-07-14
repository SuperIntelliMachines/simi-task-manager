import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies } from "../../lib/api/hooks";
import { PolicyCard } from "../../components/insurance/PolicyCard";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function LapsedPoliciesPage() {
  const { organizationId } = useWorkbench();
  const q = useListPolicies(organizationId, "lapsed");

  if (q.isLoading) return <Loading label="Loading lapsed policies..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No lapsed policies" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Lapsed Policies</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mt-4">
        {q.data.map((p) => (
          <PolicyCard key={p.id} item={p} />
        ))}
      </div>
    </div>
  );
}

export default LapsedPoliciesPage;
