import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies } from "../../lib/api/hooks";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";

export function RenewalHistoryPage() {
  const { organizationId } = useWorkbench();
  // For MVP show all policies as a simple history
  const q = useListPolicies(organizationId);

  if (q.isLoading) return <Loading label="Loading renewal history..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No renewal history" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Renewal History</h2>
      <ul className="mt-4 space-y-3">
        {q.data.map((p) => (
          <li key={p.id} className="rounded-xl bg-white p-3 shadow-sm">{p.policyholder_name} — {p.policy_number}</li>
        ))}
      </ul>
    </div>
  );
}

export default RenewalHistoryPage;
