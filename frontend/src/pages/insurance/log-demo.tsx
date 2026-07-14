import React, { useState } from "react";
import { motion } from "framer-motion";
import { useCreateLead, useStartLeadWorkflow } from "../../lib/api/hooks";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { InsuranceDatePicker } from "../../components/ui/insurance-date-picker";
import {
  addDaysToDisplayDate,
  isoDateFromDisplay,
  validateDisplayDate,
  todayDisplayDate,
} from "../../lib/utils/date-display";
import { followupDueAtFromDateInput } from "../../lib/utils/followup-schedule";
import { useNavigate } from "react-router-dom";

const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";

const textareaClassName =
  "w-full min-h-[120px] rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-3 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors resize-y";

const labelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";

export function LeadFollowupPage() {
  const { organizationId } = useWorkbench();
  const create = useCreateLead();
  const startWorkflow = useStartLeadWorkflow();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    customer_full_name: "",
    customer_phone_number: "",
    customer_email: "",
    demo_date: todayDisplayDate(),
    followup_date: addDaysToDisplayDate(todayDisplayDate(), 5),
    insurance_type: "health",
    notes: "",
  });

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.customer_full_name) {
      setError("Customer Full Name is required.");
      return;
    }
    if (!form.customer_phone_number) {
      setError("Customer Phone Number is required.");
      return;
    }
    if (form.customer_email && !form.customer_email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    const demoDateError = validateDisplayDate(form.demo_date);
    if (demoDateError) {
      setError(`Demo Date: ${demoDateError}`);
      return;
    }
    const followupDateError = validateDisplayDate(form.followup_date);
    if (followupDateError) {
      setError(`Follow-up Date: ${followupDateError}`);
      return;
    }

    const demoIso = isoDateFromDisplay(form.demo_date);
    const followupIsoDate = isoDateFromDisplay(form.followup_date);
    const demoLoggedAt = demoIso ? followupDueAtFromDateInput(demoIso) : null;
    const followupIso = followupIsoDate ? followupDueAtFromDateInput(followupIsoDate) : null;
    if (!demoLoggedAt || !followupIso) {
      setError("Please select valid demo and follow-up dates.");
      return;
    }

    try {
      const payload: Record<string, unknown> = {
        organization_id: organizationId,
        actor_user_id: null,
        contact_name: form.customer_full_name,
        contact_phone: form.customer_phone_number.trim(),
        contact_email: form.customer_email.trim() || null,
        source: "demo",
        notes: form.notes || null,
        demo_logged_at: demoLoggedAt,
        followup_due_at: followupIso,
        insurance_type: form.insurance_type || null,
        status: "follow_up_pending",
      };
      const lead = (await create.mutateAsync(payload)) as { id: number };

      try {
        await startWorkflow.mutateAsync({
          leadId: lead.id,
          body: { followup_due_at: followupIso },
        });
      } catch (wfErr: unknown) {
        const message = wfErr instanceof Error ? wfErr.message : "Failed to schedule follow-up workflow";
        setError(message);
        return;
      }

      setSuccess("Lead logged and follow-up scheduled.");
      setForm({
        customer_full_name: "",
        customer_phone_number: "",
        customer_email: "",
        demo_date: todayDisplayDate(),
        followup_date: addDaysToDisplayDate(todayDisplayDate(), 5),
        insurance_type: "health",
        notes: "",
      });
      setTimeout(() => navigate("/app/insurance/followups"), 700);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to log follow-up";
      setError(message);
    }
  }

  return (
    <div className="relative pb-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-64 w-64 rounded-full bg-[#8B5CF6]/15 blur-3xl" />
        <div className="absolute left-1/4 top-16 h-48 w-48 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative flex justify-center px-1">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="gyantra-glass-card w-full max-w-[820px] border border-white/[0.08] p-6 shadow-[0_8px_40px_rgba(0,0,0,0.45),0_0_32px_rgba(20,184,166,0.06)] md:p-8"
        >
          <header className="mb-8 border-b border-white/[0.08] pb-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-black dark:text-white md:text-4xl">Customer Follow-up Tracker</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">
              Simple follow-up workflow for insurance demos.
            </p>
          </header>

          {error ? <div className="mb-6"><ErrorState message={error} /></div> : null}
          {success ? (
            <div className="mb-6 rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-3 text-sm font-medium text-emerald-300">
              {success}
            </div>
          ) : null}

          <form className="space-y-6" onSubmit={submit}>
            <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2">
              <label className="block min-w-0">
                <div className={labelClassName}>Customer Full Name</div>
                <input
                  value={form.customer_full_name}
                  onChange={(event) => setForm({ ...form, customer_full_name: event.target.value })}
                  placeholder="Enter customer full name"
                  className={fieldClassName}
                />
              </label>

              <label className="block min-w-0">
                <div className={labelClassName}>Customer Phone Number</div>
                <input
                  value={form.customer_phone_number}
                  onChange={(event) => setForm({ ...form, customer_phone_number: event.target.value })}
                  placeholder="Enter customer phone number"
                  className={fieldClassName}
                />
              </label>
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2">
              <label className="block min-w-0">
                <div className={labelClassName}>Customer Email</div>
                <input
                  type="email"
                  value={form.customer_email}
                  onChange={(event) => setForm({ ...form, customer_email: event.target.value })}
                  placeholder="Enter customer email"
                  className={fieldClassName}
                />
              </label>

              <label className="block min-w-0">
                <div className={labelClassName}>Policy Type</div>
                <select
                  value={form.insurance_type}
                  onChange={(event) => setForm({ ...form, insurance_type: event.target.value })}
                  className={fieldClassName}
                >
                  <option value="health">Health</option>
                  <option value="life">Life</option>
                  <option value="motor">Motor</option>
                  <option value="general">General</option>
                </select>
              </label>
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2">
              <InsuranceDatePicker
                label="Demo Date"
                value={form.demo_date}
                onChange={(demo_date) => setForm({ ...form, demo_date })}
                labelClassName={labelClassName}
                inputClassName={fieldClassName}
              />
              <InsuranceDatePicker
                label="Follow-up Date"
                value={form.followup_date}
                onChange={(followup_date) => setForm({ ...form, followup_date })}
                labelClassName={labelClassName}
                inputClassName={fieldClassName}
              />
            </div>

            <label className="block">
              <div className={labelClassName}>Notes</div>
              <textarea
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
                className={textareaClassName}
              />
            </label>

            <div className="flex items-center justify-end gap-3 border-t border-white/[0.08] pt-8">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex items-center rounded-xl px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white"
              >
                Cancel
              </button>
              <button className="btn" type="submit" disabled={create.isPending || startWorkflow.isPending}>
                Log Follow-up
              </button>
              {create.isPending || startWorkflow.isPending ? <Loading label="Saving..." /> : null}
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}

export default LeadFollowupPage;
