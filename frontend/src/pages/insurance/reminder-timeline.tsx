import React from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListFollowups } from "../../lib/api/hooks";
import { Loading } from "../../components/ui/Loading";
import { EmptyState } from "../../components/ui/EmptyState";
import { FollowUpCard } from "../../components/insurance/FollowUpCard";

export function ReminderTimelinePage() {
  const { organizationId } = useWorkbench();
  const q = useListFollowups(organizationId);

  if (q.isLoading) return <Loading label="Loading reminders..." />;
  if (!q.data || q.data.length === 0) return <EmptyState message="No reminders" />;

  return (
    <div>
      <h2 className="text-xl font-semibold">Reminder Timeline</h2>
      <div className="mt-4 space-y-3">
        {q.data.map((f: any) => (
          <FollowUpCard key={f.id} item={f} />
        ))}
      </div>
    </div>
  );
}

export default ReminderTimelinePage;
