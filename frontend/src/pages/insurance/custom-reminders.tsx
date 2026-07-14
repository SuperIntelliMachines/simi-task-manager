import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useListPolicies } from "../../lib/api/hooks";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { useToast } from "../../components/ui/toast";
import Combobox from "../../components/ui/Combobox";
import { formatDate } from "../../lib/utils/formatDate";
import { formatRenewalFrequencyLabel } from "../../lib/insurance/renewal-frequency";
import type { InsurancePolicyCard } from "../../lib/api/types";
import {
  computeReminderPreview,
  getRenewalReminderValueBounds,
  PREFERRED_CHANNEL_OPTIONS,
  RENEWAL_REMINDER_UNIT_SELECT_OPTIONS,
  sanitizeReminderUnit,
  validateDoNotDisturbWindow,
  validateRenewalReminderValue,
  type ReminderUnit,
} from "../../lib/insurance/custom-reminder-config";

const labelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";
const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";
const readOnlyClassName =
  "w-full rounded-xl border border-slate-300/80 bg-white/80 dark:border-white/[0.06] dark:bg-slate-950/25 px-4 h-12 text-sm font-medium text-gray-800 dark:text-slate-300 cursor-default";
const comboboxClassName =
  "h-12 w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors";
const sectionHeadingClassName =
  "mb-5 flex items-center gap-3 text-base font-bold tracking-tight text-black dark:text-white md:text-lg";

function FormSection({
  title,
  children,
  first = false,
}: {
  title: string;
  children: React.ReactNode;
  first?: boolean;
}) {
  return (
    <section className={first ? "" : "mt-8 border-t border-white/[0.08] pt-8"}>
      <h2 className={sectionHeadingClassName}>
        <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
        {title}
      </h2>
      {children}
    </section>
  );
}

function policyLabel(policy: InsurancePolicyCard): string {
  const name = policy.policyholder_name?.trim() || "Unknown Customer";
  return `${policy.policy_number} — ${name}`;
}

export function CustomRemindersPage() {
  const { organizationId } = useWorkbench();
  const policiesQuery = useListPolicies(organizationId);
  const { showToast } = useToast();

  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [reminderUnit, setReminderUnit] = useState<ReminderUnit>("days");
  const [reminderValue, setReminderValue] = useState("7");
  const [preferredChannel, setPreferredChannel] = useState("whatsapp");
  const [dndStart, setDndStart] = useState("21:00");
  const [dndEnd, setDndEnd] = useState("08:00");
  const [reminderValueError, setReminderValueError] = useState<string | null>(null);
  const [dndError, setDndError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const policies = policiesQuery.data ?? [];

  const policyOptions = useMemo(
    () =>
      policies.map((policy) => ({
        value: String(policy.id),
        label: policyLabel(policy),
      })),
    [policies]
  );

  const selectedPolicy = useMemo(
    () => policies.find((policy) => String(policy.id) === selectedPolicyId) ?? null,
    [policies, selectedPolicyId]
  );

  const valueBounds = getRenewalReminderValueBounds(reminderUnit);

  const parsedReminderValue = Number(reminderValue);
  const preview = useMemo(() => {
    if (!selectedPolicy || !Number.isInteger(parsedReminderValue) || parsedReminderValue <= 0) {
      return null;
    }
    return computeReminderPreview(selectedPolicy.expiry_date, reminderUnit, parsedReminderValue);
  }, [selectedPolicy, reminderUnit, parsedReminderValue]);

  function handleUnitChange(rawUnit: string) {
    const nextUnit = sanitizeReminderUnit(rawUnit);
    setReminderUnit(nextUnit);
    setReminderValueError(null);
    const bounds = getRenewalReminderValueBounds(nextUnit);
    setReminderValue(String(bounds.max));
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setReminderValueError(null);
    setDndError(null);

    if (!selectedPolicy) {
      showToast("Please select a policy.", "error");
      return;
    }

    const valueError = validateRenewalReminderValue(reminderUnit, reminderValue);
    if (valueError) {
      setReminderValueError(valueError);
      return;
    }

    const windowError = validateDoNotDisturbWindow(dndStart, dndEnd);
    if (windowError) {
      setDndError(windowError);
      return;
    }

    setIsSaving(true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 400));
      showToast("Renewal reminder configuration saved.", "success");
    } finally {
      setIsSaving(false);
    }
  }

  if (organizationId == null) {
    return <Loading label="Loading organization..." />;
  }

  if (policiesQuery.isLoading) {
    return <Loading label="Loading policies..." />;
  }

  if (policiesQuery.isError) {
    return <ErrorState message="Failed to load policies for renewal reminders." />;
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
          className="gyantra-glass-card w-full max-w-[820px] rounded-[20px] border border-white/[0.08] p-6 shadow-[0_8px_40px_rgba(0,0,0,0.45),0_0_32px_rgba(20,184,166,0.06)] md:p-8"
        >
          <header className="mb-8 border-b border-white/[0.08] pb-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-black dark:text-white md:text-4xl">Renewal Reminders</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">
              Configure personalized renewal reminder schedules for selected policies based on customer
              preferences. This is separate from the default automated reminder workflow.
            </p>
          </header>

          <form className="space-y-0" onSubmit={handleSave}>
            <FormSection title="Policy Selection" first>
              <div className="space-y-6">
                <label className="block">
                  <span className={labelClassName}>Policy</span>
                  <Combobox
                    items={policyOptions}
                    value={selectedPolicyId || null}
                    onChange={(value) => setSelectedPolicyId(value ?? "")}
                    placeholder="Search by Policy Number or Policy Holder Name"
                    searchable
                    className={comboboxClassName}
                  />
                </label>

                {selectedPolicy ? (
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <label className="block">
                      <span className={labelClassName}>Customer Name</span>
                      <input
                        readOnly
                        value={selectedPolicy.policyholder_name ?? "—"}
                        className={readOnlyClassName}
                      />
                    </label>
                    <label className="block">
                      <span className={labelClassName}>Policy Type</span>
                      <input readOnly value={selectedPolicy.policy_type ?? "—"} className={readOnlyClassName} />
                    </label>
                    <label className="block">
                      <span className={labelClassName}>Renewal Frequency</span>
                      <input
                        readOnly
                        value={formatRenewalFrequencyLabel(selectedPolicy.renewal_frequency)}
                        className={readOnlyClassName}
                      />
                    </label>
                    <label className="block">
                      <span className={labelClassName}>Expiry Date</span>
                      <input
                        readOnly
                        value={formatDate(selectedPolicy.expiry_date)}
                        className={readOnlyClassName}
                      />
                    </label>
                  </div>
                ) : null}
              </div>
            </FormSection>

            <FormSection title="Reminder Schedule">
              <div className="space-y-6">
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                  <label className="block" htmlFor="renewal-reminder-unit">
                    <span className={labelClassName}>Reminder Unit</span>
                    <select
                      id="renewal-reminder-unit"
                      name="renewal_reminder_unit"
                      autoComplete="off"
                      value={reminderUnit}
                      onChange={(event) => handleUnitChange(event.target.value)}
                      className={fieldClassName}
                    >
                      {RENEWAL_REMINDER_UNIT_SELECT_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block" htmlFor="renewal-reminder-value">
                    <span className={labelClassName}>
                      Reminder Value ({valueBounds.min}–{valueBounds.max})
                    </span>
                    <input
                      id="renewal-reminder-value"
                      name="renewal_reminder_value"
                      autoComplete="off"
                      type="number"
                      min={valueBounds.min}
                      max={valueBounds.max}
                      step={1}
                      value={reminderValue}
                      onChange={(event) => {
                        setReminderValueError(null);
                        setReminderValue(event.target.value);
                      }}
                      onBlur={() =>
                        setReminderValueError(validateRenewalReminderValue(reminderUnit, reminderValue))
                      }
                      className={`${fieldClassName}${reminderValueError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
                      required
                    />
                    {reminderValueError ? (
                      <p className="mt-2 text-sm text-red-400">{reminderValueError}</p>
                    ) : null}
                  </label>
                </div>

                <div className="rounded-xl border border-[#14B8A6]/30 bg-gradient-to-br from-[#14B8A6]/12 via-[#14B8A6]/5 to-slate-950/30 px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_0_24px_rgba(20,184,166,0.08)]">
                  <p className="text-sm font-semibold tracking-wide text-[#14B8A6]">Reminder Preview</p>
                  {preview ? (
                    <div className="mt-3 space-y-2 border-t border-[#14B8A6]/20 pt-3">
                      <p className="text-sm">
                        <span className="text-slate-400">Reminder Date:</span>{" "}
                        <span className="font-medium text-white">{preview.reminderDate}</span>
                      </p>
                      <p className="text-sm">
                        <span className="text-slate-400">Day:</span>{" "}
                        <span className="font-medium text-white">{preview.reminderDay}</span>
                      </p>
                      {preview.reminderTime ? (
                        <p className="text-sm">
                          <span className="text-slate-400">Time:</span>{" "}
                          <span className="font-medium text-white">{preview.reminderTime}</span>
                        </p>
                      ) : null}
                    </div>
                  ) : (
                    <p className="mt-3 border-t border-[#14B8A6]/20 pt-3 text-sm text-slate-400">
                      Select a policy and enter a valid reminder value to preview the schedule.
                    </p>
                  )}
                </div>
              </div>
            </FormSection>

            <FormSection title="Delivery Preferences">
              <div className="space-y-6">
                <label className="block max-w-md">
                  <span className={labelClassName}>Preferred Channel</span>
                  <select
                    value={preferredChannel}
                    onChange={(event) => setPreferredChannel(event.target.value)}
                    className={fieldClassName}
                  >
                    {PREFERRED_CHANNEL_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <div>
                  <p className={`${labelClassName} mb-3`}>Do Not Disturb Hours</p>
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <label className="block" htmlFor="renewal-dnd-start">
                      <span className={labelClassName}>Start Time</span>
                      <input
                        id="renewal-dnd-start"
                        name="renewal_dnd_start"
                        autoComplete="off"
                        type="time"
                        value={dndStart}
                        onChange={(event) => {
                          setDndError(null);
                          setDndStart(event.target.value);
                        }}
                        className={fieldClassName}
                        required
                      />
                    </label>
                    <label className="block" htmlFor="renewal-dnd-end">
                      <span className={labelClassName}>End Time</span>
                      <input
                        id="renewal-dnd-end"
                        name="renewal_dnd_end"
                        autoComplete="off"
                        type="time"
                        value={dndEnd}
                        onChange={(event) => {
                          setDndError(null);
                          setDndEnd(event.target.value);
                        }}
                        className={fieldClassName}
                        required
                      />
                    </label>
                  </div>
                  {dndError ? <p className="mt-2 text-sm text-red-400">{dndError}</p> : null}
                </div>
              </div>
            </FormSection>

            <div className="mt-8 flex justify-end border-t border-white/[0.08] pt-8">
              <button className="btn" type="submit" disabled={isSaving}>
                {isSaving ? "Saving..." : "Save Renewal Reminder"}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}

export default CustomRemindersPage;
