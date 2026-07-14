import React, { useMemo, useState } from "react";
import { followupDueAtFromDateInput, followupDueAtFromDays } from "../../lib/utils/followup-schedule";
import { formatDate } from "../../lib/utils/formatDate";

type ScheduleOption = "5" | "10" | "custom";

type FollowUpLaterModalProps = {
  open: boolean;
  customerName?: string;
  isSubmitting?: boolean;
  onClose: () => void;
  onConfirm: (followupDueAtIso: string) => void;
};

export function FollowUpLaterModal({
  open,
  customerName,
  isSubmitting = false,
  onClose,
  onConfirm,
}: FollowUpLaterModalProps) {
  const [schedule, setSchedule] = useState<ScheduleOption>("5");
  const [customDate, setCustomDate] = useState("");

  const previewIso = useMemo(() => {
    if (schedule === "custom") {
      return followupDueAtFromDateInput(customDate);
    }
    return followupDueAtFromDays(schedule === "10" ? 10 : 5);
  }, [schedule, customDate]);

  if (!open) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!previewIso) return;
    onConfirm(previewIso);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="Close follow-up schedule dialog"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="follow-up-later-title"
        className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="follow-up-later-title" className="text-lg font-semibold text-slate-900 dark:text-white">
          Schedule Follow-up
        </h2>
        {customerName ? (
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Customer: {customerName}</p>
        ) : null}

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-700 dark:text-slate-300">When should we follow up?</legend>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
              <input
                type="radio"
                name="followup_schedule"
                value="5"
                checked={schedule === "5"}
                onChange={() => setSchedule("5")}
              />
              <span className="text-sm text-slate-800 dark:text-slate-200">In 5 days</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
              <input
                type="radio"
                name="followup_schedule"
                value="10"
                checked={schedule === "10"}
                onChange={() => setSchedule("10")}
              />
              <span className="text-sm text-slate-800 dark:text-slate-200">In 10 days</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
              <input
                type="radio"
                name="followup_schedule"
                value="custom"
                checked={schedule === "custom"}
                onChange={() => setSchedule("custom")}
              />
              <span className="text-sm text-slate-800 dark:text-slate-200">Custom date</span>
            </label>
          </fieldset>

          {schedule === "custom" ? (
            <label className="block">
              <span className="text-sm text-slate-700 dark:text-slate-300">Follow-up date</span>
              <input
                type="date"
                required
                value={customDate}
                onChange={(e) => setCustomDate(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
          ) : null}

          <p className="text-sm text-slate-600 dark:text-slate-400">
            New follow-up date:{" "}
            <span className="font-medium text-slate-900 dark:text-white">
              {previewIso ? formatDate(previewIso) : "Select a valid date"}
            </span>
          </p>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !previewIso}
              className="rounded-xl bg-[#14B8A6] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0d9488] disabled:opacity-50"
            >
              {isSubmitting ? "Saving..." : "Reschedule Follow-up"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default FollowUpLaterModal;
