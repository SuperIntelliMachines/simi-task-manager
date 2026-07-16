import { useEffect, useMemo, useState } from "react";

import { ReminderSchedulingFields } from "../reminder-management/ReminderSchedulingFields";
import { PlatformDialog } from "../platform/platform-dialog";
import Combobox from "../ui/Combobox";
import { Button } from "../ui/button";
import {
  buildDefaultClaimsReminderForm,
  CLAIMS_REMINDER_CHANNELS,
  CLAIMS_REMINDER_ENTITY_TYPE,
  CLAIMS_REMINDER_OFFSET_UNITS,
  CLAIMS_REMINDER_RECIPIENTS,
  DEFAULT_CLAIMS_REMINDER_FORM,
  type ClaimsReminderFormValues,
} from "../../lib/claims/reminder-settings";
import { useReminderModuleConfig } from "../../lib/reminder-management/hooks";
import {
  findModuleTrigger,
  toTriggerComboboxItems,
} from "../../lib/reminder-management/module-config";
import type { ReminderStopCondition } from "../../lib/reminder-management/types";

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
  const moduleConfigQuery = useReminderModuleConfig(CLAIMS_REMINDER_ENTITY_TYPE);
  const moduleConfig = moduleConfigQuery.data;

  const [form, setForm] = useState<ClaimsReminderFormValues>(DEFAULT_CLAIMS_REMINDER_FORM);
  const [error, setError] = useState<string | null>(null);

  const triggerItems = useMemo(() => toTriggerComboboxItems(moduleConfig), [moduleConfig]);
  const stopConditionOptions = useMemo(
    () =>
      (moduleConfig?.stopConditions ?? []).map((item) => ({
        value: item.id,
        label: item.label,
      })),
    [moduleConfig?.stopConditions]
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
    const defaults = buildDefaultClaimsReminderForm(moduleConfig);
    const next = initialValues ?? defaults;
    // Ensure triggerKind matches metadata when editing an older rule.
    const matched = findModuleTrigger(moduleConfig, next.triggerKey);
    setForm({
      ...next,
      triggerKind: matched?.kind ?? next.triggerKind,
      triggerKey: next.triggerKey || defaults.triggerKey,
    });
    setError(null);
  }, [open, initialValues, moduleConfig]);

  function update<K extends keyof ClaimsReminderFormValues>(key: K, value: ClaimsReminderFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSave() {
    if (!form.triggerKey.trim()) {
      setError(
        triggerItems.length === 0
          ? "No triggers are available for Claims yet."
          : "Select a trigger."
      );
      return;
    }
    if (!Number.isFinite(form.offsetValue) || form.offsetValue < 0) {
      setError("Offset must be zero or a positive number.");
      return;
    }
    if (!Number.isInteger(form.offsetValue)) {
      setError("Offset must be a whole number.");
      return;
    }
    if (form.repeatEnabled) {
      if (!Number.isFinite(form.repeatFrequencyValue) || form.repeatFrequencyValue < 1) {
        setError("Repeat frequency must be at least 1 when repeat is enabled.");
        return;
      }
    }
    if (form.maxAttempts != null && form.maxAttempts < 1) {
      setError("Maximum attempts must be at least 1 when provided.");
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
          <Button onClick={handleSave} disabled={saving || moduleConfigQuery.isLoading}>
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
            value={form.triggerKey || null}
            onChange={(value) => {
              const selected = findModuleTrigger(moduleConfig, value || "");
              setForm((current) => ({
                ...current,
                triggerKey: value || "",
                triggerKind: selected?.kind ?? current.triggerKind,
              }));
            }}
            placeholder={
              moduleConfigQuery.isLoading
                ? "Loading triggers…"
                : triggerItems.length === 0
                  ? "No triggers available"
                  : "Select trigger"
            }
            searchable={false}
            className={comboboxClassName}
          />
          {!moduleConfigQuery.isLoading && triggerItems.length === 0 ? (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              No triggers returned by Claims module metadata.
            </p>
          ) : null}
        </label>

        <ReminderSchedulingFields
          value={{
            offsetValue: form.offsetValue,
            offsetUnit: form.offsetUnit,
            offsetDirection: form.direction,
            repeatEnabled: form.repeatEnabled,
            repeatFrequencyValue: form.repeatFrequencyValue,
            repeatFrequencyUnit: form.repeatFrequencyUnit,
            maxAttempts: form.maxAttempts,
            stopCondition: form.stopCondition,
          }}
          onChange={(patch) => {
            if (patch.offsetValue !== undefined) update("offsetValue", patch.offsetValue);
            if (patch.offsetUnit !== undefined) {
              update("offsetUnit", patch.offsetUnit as ClaimsReminderFormValues["offsetUnit"]);
            }
            if (patch.offsetDirection !== undefined) update("direction", patch.offsetDirection);
            if (patch.repeatEnabled !== undefined) update("repeatEnabled", patch.repeatEnabled);
            if (patch.repeatFrequencyValue !== undefined) {
              update("repeatFrequencyValue", patch.repeatFrequencyValue);
            }
            if (patch.repeatFrequencyUnit !== undefined) {
              update(
                "repeatFrequencyUnit",
                patch.repeatFrequencyUnit as ClaimsReminderFormValues["repeatFrequencyUnit"]
              );
            }
            if (patch.maxAttempts !== undefined) update("maxAttempts", patch.maxAttempts);
            if (patch.stopCondition !== undefined) {
              update("stopCondition", patch.stopCondition as ReminderStopCondition);
            }
          }}
          offsetUnitOptions={CLAIMS_REMINDER_OFFSET_UNITS.map((item) => ({
            value: item.key,
            label: item.label,
          }))}
          stopConditionOptions={
            stopConditionOptions.length > 0 ? stopConditionOptions : undefined
          }
        />

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
