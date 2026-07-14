import { useEffect, useMemo, useState } from "react";

import { PlatformDialog } from "../platform/platform-dialog";
import Combobox from "../ui/Combobox";
import { Button } from "../ui/button";
import {
  CLAIMS_REMINDER_CHANNELS,
  CLAIMS_REMINDER_OFFSET_UNITS,
  CLAIMS_REMINDER_RECIPIENTS,
  CLAIMS_REMINDER_TRIGGERS,
  DEFAULT_CLAIMS_REMINDER_FORM,
  type ClaimsReminderFormValues,
} from "../../lib/claims/reminder-settings";

/** Match Insurance create-policy / policy-details field styling. */
const labelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";
const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";
const comboboxClassName =
  "h-12 w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors";

type ClaimsReminderRuleDialogProps = {
  open: boolean;
  mode: "create" | "edit";
  initialValues?: ClaimsReminderFormValues | null;
  saving?: boolean;
  onClose: () => void;
  onSave: (values: ClaimsReminderFormValues) => void;
};

export function ClaimsReminderRuleDialog({
  open,
  mode,
  initialValues,
  saving = false,
  onClose,
  onSave,
}: ClaimsReminderRuleDialogProps) {
  const [form, setForm] = useState<ClaimsReminderFormValues>(DEFAULT_CLAIMS_REMINDER_FORM);
  const [error, setError] = useState<string | null>(null);

  const triggerItems = useMemo(
    () => CLAIMS_REMINDER_TRIGGERS.map((item) => ({ value: item.key, label: item.label })),
    []
  );
  const offsetUnitItems = useMemo(
    () => CLAIMS_REMINDER_OFFSET_UNITS.map((item) => ({ value: item.key, label: item.label })),
    []
  );
  const channelItems = useMemo(
    () => CLAIMS_REMINDER_CHANNELS.map((item) => ({ value: item.key, label: item.label })),
    []
  );
  const recipientItems = useMemo(
    () => CLAIMS_REMINDER_RECIPIENTS.map((item) => ({ value: item.key, label: item.label })),
    []
  );

  useEffect(() => {
    if (!open) return;
    setForm(initialValues ?? DEFAULT_CLAIMS_REMINDER_FORM);
    setError(null);
  }, [open, initialValues]);

  function update<K extends keyof ClaimsReminderFormValues>(key: K, value: ClaimsReminderFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSave() {
    if (!Number.isFinite(form.offsetValue) || form.offsetValue < 0) {
      setError("Offset must be zero or a positive number.");
      return;
    }
    if (!Number.isInteger(form.offsetValue)) {
      setError("Offset must be a whole number.");
      return;
    }
    setError(null);
    onSave(form);
  }

  return (
    <PlatformDialog
      open={open}
      title={mode === "create" ? "Create Reminder" : "Edit Reminder"}
      description="Configure when Claims staff should be reminded about a workflow stage."
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="grid gap-5">
        <label className="block">
          <span className={labelClassName}>Trigger</span>
          <Combobox
            items={triggerItems}
            value={form.triggerKey}
            onChange={(value) =>
              update("triggerKey", (value ?? DEFAULT_CLAIMS_REMINDER_FORM.triggerKey) as ClaimsReminderFormValues["triggerKey"])
            }
            placeholder="Select trigger"
            searchable={false}
            className={comboboxClassName}
          />
        </label>

        <fieldset>
          <legend className={labelClassName}>Timing</legend>
          <div className="flex flex-wrap gap-4">
            {(["before", "after"] as const).map((direction) => (
              <label
                key={direction}
                className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-800 dark:text-slate-200"
              >
                <input
                  type="radio"
                  name="claims-reminder-timing"
                  className="h-4 w-4 accent-[#14B8A6]"
                  checked={form.direction === direction}
                  onChange={() => update("direction", direction)}
                />
                <span className="capitalize">{direction}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <span className={labelClassName}>Offset</span>
          <div className="grid grid-cols-[1fr_1fr] gap-3">
            <input
              type="number"
              min={0}
              step={1}
              className={fieldClassName}
              value={form.offsetValue}
              onChange={(event) => update("offsetValue", Number(event.target.value))}
              aria-label="Offset value"
            />
            <Combobox
              items={offsetUnitItems}
              value={form.offsetUnit}
              onChange={(value) =>
                update(
                  "offsetUnit",
                  (value ?? DEFAULT_CLAIMS_REMINDER_FORM.offsetUnit) as ClaimsReminderFormValues["offsetUnit"]
                )
              }
              placeholder="Select unit"
              searchable={false}
              className={comboboxClassName}
            />
          </div>
        </div>

        <label className="block">
          <span className={labelClassName}>Channel</span>
          <Combobox
            items={channelItems}
            value={form.channelKey}
            onChange={(value) =>
              update(
                "channelKey",
                (value ?? DEFAULT_CLAIMS_REMINDER_FORM.channelKey) as ClaimsReminderFormValues["channelKey"]
              )
            }
            placeholder="Select channel"
            searchable={false}
            className={comboboxClassName}
          />
        </label>

        <label className="block">
          <span className={labelClassName}>Recipient</span>
          <Combobox
            items={recipientItems}
            value={form.recipientKey}
            onChange={(value) =>
              update(
                "recipientKey",
                (value ?? DEFAULT_CLAIMS_REMINDER_FORM.recipientKey) as ClaimsReminderFormValues["recipientKey"]
              )
            }
            placeholder="Select recipient"
            searchable={false}
            className={comboboxClassName}
          />
        </label>

        <label className="inline-flex cursor-pointer items-center gap-3 text-sm font-medium text-gray-800 dark:text-slate-200">
          <input
            type="checkbox"
            className="h-4 w-4 rounded accent-[#14B8A6]"
            checked={form.enabled}
            onChange={(event) => update("enabled", event.target.checked)}
          />
          Enabled
        </label>

        {error ? <p className="text-sm font-medium text-rose-500">{error}</p> : null}
      </div>
    </PlatformDialog>
  );
}
