import React, { useState } from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useCreateLead, useStartLeadWorkflow } from "../../lib/api/hooks";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { useNavigate } from "react-router-dom";
import type { InsuranceLeadCard } from "../../lib/api/types";

export function CreateLeadPage() {
  const { organizationId } = useWorkbench();
  const create = useCreateLead();
  const startWorkflow = useStartLeadWorkflow();
  const navigate = useNavigate();
  const [form, setForm] = useState({ contact_name: "", assigned_agent_user_id: "", source: "", notes: "", followup_due_at: "" });
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.contact_name) {
      setError("Customer Full Name is required.");
      return;
    }
    try {
      const lead = (await create.mutateAsync({
        organization_id: organizationId,
        actor_user_id: null,
        contact_name: form.contact_name,
        assigned_agent_user_id: form.assigned_agent_user_id ? Number(form.assigned_agent_user_id) : null,
        source: form.source || null,
        notes: form.notes || null,
        followup_due_at: form.followup_due_at ? new Date(form.followup_due_at).toISOString() : null,
      })) as InsuranceLeadCard;
      // start follow-up workflow to create reminder/task
      try {
        await startWorkflow.mutateAsync({ leadId: lead.id, body: { followup_due_at: form.followup_due_at ? new Date(form.followup_due_at).toISOString() : undefined, days_until_followup: 5 } });
      } catch {
        // ignore workflow start errors but keep the lead
      }
      navigate("/app/insurance/followups");
    } catch (e: any) {
      setError(e?.message ?? "Failed to create lead");
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Create Lead</h2>
      {error ? <ErrorState message={error} /> : null}
      <form className="space-y-3 mt-4" onSubmit={submit}>
        <label className="block">
          <div className="text-sm text-slate-700 dark:text-slate-300">Customer Full Name</div>
          <input value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} placeholder="Enter customer full name" className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700" />
        </label>
        <label className="block">
          <div className="text-sm text-slate-700 dark:text-slate-300">Assigned Agent (user id)</div>
          <input value={form.assigned_agent_user_id} onChange={(e) => setForm({ ...form, assigned_agent_user_id: e.target.value })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700" />
        </label>
        <label className="block">
          <div className="text-sm text-slate-700 dark:text-slate-300">Source</div>
          <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700" />
        </label>
        <label className="block">
          <div className="text-sm text-slate-700 dark:text-slate-300">Notes</div>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700" />
        </label>
        <label className="block">
          <div className="text-sm text-slate-700 dark:text-slate-300">Follow-up Date</div>
          <input type="datetime-local" value={form.followup_due_at} onChange={(e) => setForm({ ...form, followup_due_at: e.target.value })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700" />
        </label>
        <div>
          <button className="btn" type="submit" disabled={create.isPending}>Create Lead</button>
          {create.isPending ? <Loading label="Creating..." /> : null}
        </div>
      </form>
    </div>
  );
}

export default CreateLeadPage;
