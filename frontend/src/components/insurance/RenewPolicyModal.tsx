import React, { useEffect, useMemo, useState } from "react";
import { InsuranceDatePicker } from "../ui/insurance-date-picker";
import {
  isoDateFromDisplay,
  toDisplayDate,
  validateRenewalExpiryDate,
} from "../../lib/utils/date-display";

type RenewPolicyModalProps = {
  open: boolean;
  currentExpiryDate: string;
  isSubmitting?: boolean;
  onClose: () => void;
  onConfirm: (payload: { newExpiryDate: string; renewalNotes: string }) => void;
};

const readOnlyClassName =
  "w-full rounded-md border border-slate-200 bg-slate-50 px-3 h-12 text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300";

export function RenewPolicyModal({
  open,
  currentExpiryDate,
  isSubmitting = false,
  onClose,
  onConfirm,
}: RenewPolicyModalProps) {
  const [newExpiryDate, setNewExpiryDate] = useState("");
  const [renewalNotes, setRenewalNotes] = useState("");
  const [showValidation, setShowValidation] = useState(false);

  const currentExpiryDisplay = useMemo(() => toDisplayDate(currentExpiryDate), [currentExpiryDate]);

  const dateError = useMemo(
    () => validateRenewalExpiryDate(newExpiryDate, currentExpiryDate),
    [newExpiryDate, currentExpiryDate],
  );

  const canConfirmRenewal = Boolean(newExpiryDate.trim()) && dateError == null && !isSubmitting;

  useEffect(() => {
    if (!open) return;
    setNewExpiryDate("");
    setRenewalNotes("");
    setShowValidation(false);
  }, [open, currentExpiryDate]);

  if (!open) return null;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setShowValidation(true);

    const validationError = validateRenewalExpiryDate(newExpiryDate, currentExpiryDate);
    if (validationError) {
      return;
    }

    const isoDate = isoDateFromDisplay(newExpiryDate.trim());
    if (!isoDate) {
      return;
    }

    onConfirm({ newExpiryDate: isoDate, renewalNotes });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-label="Close renew policy dialog"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="renew-policy-title"
        className="relative w-full max-w-lg rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xl backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/90 glass-card"
      >
        <h2 id="renew-policy-title" className="text-lg font-semibold text-slate-900 dark:text-white">
          Renew Policy
        </h2>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-sm text-slate-700 dark:text-slate-300">Current Expiry Date</span>
            <input
              type="text"
              readOnly
              value={currentExpiryDisplay}
              className={`${readOnlyClassName} mt-2`}
            />
          </label>

          <InsuranceDatePicker
            label="New Expiry Date *"
            value={newExpiryDate}
            onChange={setNewExpiryDate}
            onBlur={() => setShowValidation(true)}
            error={showValidation || newExpiryDate.trim() ? dateError : null}
          />

          <label className="block">
            <span className="text-sm text-slate-700 dark:text-slate-300">Renewal Notes</span>
            <textarea
              value={renewalNotes}
              onChange={(event) => setRenewalNotes(event.target.value)}
              rows={3}
              placeholder="Optional notes about this renewal"
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:border-slate-700 dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500"
            />
          </label>

          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
            Renewing a policy will cancel all future reminders for the current policy term and create a new reminder
            schedule based on the new expiry date.
          </p>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="inline-flex items-center px-4 py-2 rounded-md text-sm text-slate-700 dark:text-slate-300 hover:bg-sidebar-accent disabled:opacity-60"
            >
              Cancel
            </button>
            <button className="btn" type="submit" disabled={!canConfirmRenewal}>
              {isSubmitting ? "Renewing..." : "Confirm Renewal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RenewPolicyModal;
