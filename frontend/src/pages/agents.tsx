import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { DashboardCard } from "../components/workbench/dashboard-card";
import { Button } from "../components/ui/button";
import { useApprovalRequests, useCommandPreview } from "../lib/api/hooks";
import { useWorkbench } from "../app/providers/workbench-provider";

const commandSchema = z.object({
  command: z.string().min(6, "Enter a more specific command."),
});

type CommandForm = z.infer<typeof commandSchema>;

export function AgentsPage() {
  const { organizationId } = useWorkbench();
  const approvalsQuery = useApprovalRequests(organizationId);
  const previewMutation = useCommandPreview();
  const [executed, setExecuted] = useState<string | null>(null);
  const form = useForm<CommandForm>({
    resolver: zodResolver(commandSchema),
    defaultValues: { command: "Send renewal reminders to all expiring customers" },
  });

  const handlePreview = form.handleSubmit(async (values) => {
    setExecuted(null);
    await previewMutation.mutateAsync(values.command);
  });

  const handleExecute = form.handleSubmit(async (values) => {
    const preview = await previewMutation.mutateAsync(values.command);
    setExecuted(preview.resultMessage ?? "Command executed.");
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
      <DashboardCard title="AI Command Bar" eyebrow="Agents">
        <form className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="command-input">
              Natural language command
            </label>
            <textarea
              id="command-input"
              className="mt-2 min-h-28 w-full rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900"
              {...form.register("command")}
            />
            {form.formState.errors.command ? (
              <p className="mt-2 text-sm text-rose-600">{form.formState.errors.command.message}</p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => void handlePreview()}>
              Preview Action
            </Button>
            <Button type="button" variant="outline" onClick={() => void handleExecute()}>
              Run Command
            </Button>
          </div>
        </form>

        {previewMutation.data ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Extracted Action Preview</p>
              <p className="mt-2 text-sm text-slate-700">Domain: <span className="font-medium">{previewMutation.data.domain}</span></p>
              <p className="mt-1 text-sm text-slate-700">Confidence: <span className="font-medium">{Math.round(previewMutation.data.confidence * 100)}%</span></p>
              <p className="mt-3 text-sm text-slate-700">Extracted fields</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {previewMutation.data.extractedFields.map((field) => (
                  <span key={field} className="rounded-full bg-white px-3 py-1 text-xs text-slate-700 ring-1 ring-slate-200">{field}</span>
                ))}
              </div>
            </div>
            <div className="rounded-3xl bg-slate-50 p-4" data-testid="command-preview-state">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Execution State</p>
              <p className="mt-2 text-sm font-medium capitalize text-slate-900">{previewMutation.data.status.replace(/_/g, " ")}</p>
              {previewMutation.data.missingFields.length ? (
                <p className="mt-2 text-sm text-amber-700">Missing fields: {previewMutation.data.missingFields.join(", ")}</p>
              ) : null}
              {previewMutation.data.approvalReason ? (
                <p className="mt-2 text-sm text-rose-700">Approval required: {previewMutation.data.approvalReason}</p>
              ) : null}
              {executed ? <p className="mt-2 text-sm text-emerald-700">{executed}</p> : null}
            </div>
          </div>
        ) : null}
      </DashboardCard>

      <DashboardCard title="Approval Queue" eyebrow="Guardrails">
        {approvalsQuery.isLoading ? <p className="text-sm text-slate-500">Loading approvals...</p> : null}
        <div className="space-y-3">
          {(approvalsQuery.data ?? []).map((approval) => (
            <div key={approval.id} className="rounded-3xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-medium text-slate-900">{approval.proposed_action.action_type}</p>
              <p className="mt-1 text-sm text-slate-600">{approval.reason}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">Status: {approval.status}</p>
            </div>
          ))}
        </div>
      </DashboardCard>
    </div>
  );
}
